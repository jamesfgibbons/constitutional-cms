#!/usr/bin/env python3
"""
Constitutional CMS Contract Validator

Validates that contract YAML files are internally consistent.
Does NOT validate live site compliance — that's your eval harness.
This validates the contracts themselves.

Usage:
    python scripts/validate_contracts.py
    python scripts/validate_contracts.py --contracts-dir ./contracts
    python scripts/validate_contracts.py --check page_types
    python scripts/validate_contracts.py --check links
    python scripts/validate_contracts.py --check enrichment
    python scripts/validate_contracts.py --check boundary
"""

import yaml
import sys
import os
import argparse
from pathlib import Path


def load_yaml(filepath: str) -> dict:
    """Load and parse a YAML file."""
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def validate_page_types(contracts_dir: str) -> list[str]:
    """Validate page_types.yaml internal consistency."""
    errors = []
    filepath = os.path.join(contracts_dir, 'page_types.yaml')
    
    if not os.path.exists(filepath):
        return [f"MISSING: {filepath}"]
    
    data = load_yaml(filepath)
    
    for page_type, config in data.items():
        if not isinstance(config, dict):
            continue
            
        tiers = config.get('tiers', {})
        
        # Every page type must have at least FULL and SHELL
        if 'FULL' not in tiers:
            errors.append(f"{page_type}: missing FULL tier definition")
        if 'SHELL' not in tiers:
            errors.append(f"{page_type}: missing SHELL tier definition")
        
        # FULL must have more required_fields than BASIC
        full_fields = len(tiers.get('FULL', {}).get('required_fields', []))
        basic_fields = len(tiers.get('BASIC', {}).get('required_fields', []))
        if basic_fields > 0 and full_fields <= basic_fields:
            errors.append(f"{page_type}: FULL tier should require more fields than BASIC")
        
        # SHELL must not emit schema
        shell = tiers.get('SHELL', {})
        if shell.get('schema_emission', False):
            errors.append(f"{page_type}: SHELL tier must not emit schema (schema_emission should be false)")
        
        # SHELL must not emit internal links
        if shell.get('internal_links', False):
            errors.append(f"{page_type}: SHELL tier must not emit internal links")
        
        # Must have a url_pattern
        if 'url_pattern' not in config:
            errors.append(f"{page_type}: missing url_pattern")
        
        # Degradation rules should reference valid tiers
        for rule in config.get('degradation_rules', []):
            action = rule.get('action', '')
            for tier_name in ['FULL', 'BASIC', 'SHELL', 'SUPPRESS']:
                if tier_name in action and tier_name not in tiers:
                    errors.append(f"{page_type}: degradation rule references {tier_name} but tier is not defined")
    
    return errors


def validate_enrichment_stages(contracts_dir: str) -> list[str]:
    """Validate enrichment_stages.yaml internal consistency."""
    errors = []
    filepath = os.path.join(contracts_dir, 'enrichment_stages.yaml')
    
    if not os.path.exists(filepath):
        return [f"MISSING: {filepath}"]
    
    data = load_yaml(filepath)
    stages = data.get('stages', [])
    
    # Track write targets to ensure single-writer rule
    write_targets = {}
    
    for stage in stages:
        name = stage.get('name', 'unnamed')
        owner = stage.get('owner')
        writes_to = stage.get('writes_to')
        
        # Every stage must have an owner
        if not owner:
            errors.append(f"Stage '{name}': missing owner")
        
        # Every stage must have a writes_to
        if not writes_to:
            errors.append(f"Stage '{name}': missing writes_to")
        
        # Single-writer enforcement
        if writes_to:
            # Handle dotted paths (e.g., entity_snapshots.narrative_block)
            base_table = writes_to.split('.')[0] if '.' in str(writes_to) else writes_to
            if base_table in write_targets and write_targets[base_table] != owner:
                errors.append(
                    f"SINGLE-WRITER VIOLATION: '{name}' ({owner}) and "
                    f"'{write_targets[base_table]}' both write to '{base_table}'"
                )
            # Allow column-level writes by different owners on the same table
            # Only flag if two owners write to the exact same target
            if writes_to in write_targets and write_targets[writes_to] != owner:
                errors.append(
                    f"WRITE CONFLICT: '{name}' ({owner}) writes to '{writes_to}' "
                    f"but it's already owned by {write_targets[writes_to]}"
                )
            write_targets[writes_to] = owner
        
        # Quality gates should exist
        if not stage.get('quality_gate'):
            errors.append(f"Stage '{name}': missing quality_gate (every stage needs validation)")
    
    return errors


def validate_link_rules(contracts_dir: str) -> list[str]:
    """Validate link_rules.yaml internal consistency."""
    errors = []
    filepath = os.path.join(contracts_dir, 'link_rules.yaml')
    
    if not os.path.exists(filepath):
        return [f"MISSING: {filepath}"]
    
    data = load_yaml(filepath)
    rules = data.get('rules', [])
    
    has_phantom_rule = False
    has_shell_rule = False
    
    for rule in rules:
        name = rule.get('name', 'unnamed')
        
        if not rule.get('enforcement'):
            errors.append(f"Link rule '{name}': missing enforcement level (hard_block or soft_warn)")
        
        if name == 'no_phantom_links':
            has_phantom_rule = True
        if name == 'shell_isolation':
            has_shell_rule = True
    
    # These two rules are mandatory for any Constitutional CMS deployment
    if not has_phantom_rule:
        errors.append("REQUIRED: 'no_phantom_links' rule must exist — this is a core Constitutional CMS principle")
    if not has_shell_rule:
        errors.append("REQUIRED: 'shell_isolation' rule must exist — SHELL pages must not emit links")
    
    return errors


def validate_snapshot_boundary(contracts_dir: str) -> list[str]:
    """Validate snapshot_boundary.yaml internal consistency."""
    errors = []
    filepath = os.path.join(contracts_dir, 'snapshot_boundary.yaml')
    
    if not os.path.exists(filepath):
        return [f"MISSING: {filepath}"]
    
    data = load_yaml(filepath)
    boundaries = data.get('boundaries', {})
    
    write_agents = set(boundaries.get('write_agents', []))
    read_agents = set(boundaries.get('read_agents', []))
    
    # No agent should be both writer and reader
    overlap = write_agents & read_agents
    if overlap:
        errors.append(f"BOUNDARY VIOLATION: {overlap} appears in both write_agents and read_agents")
    
    # Must have at least one write agent and one read agent
    if not write_agents:
        errors.append("No write agents defined")
    if not read_agents:
        errors.append("No read agents defined")
    
    # Must define failure mode
    if data.get('failure_mode') != 'fail_safe_not_silent':
        errors.append("failure_mode should be 'fail_safe_not_silent' — Constitutional CMS requires safe degradation")
    
    return errors


def validate_yaml_syntax(contracts_dir: str) -> list[str]:
    """Validate every YAML contract can be parsed."""
    errors = []
    for filepath in sorted(Path(contracts_dir).rglob("*.yaml")):
        try:
            load_yaml(str(filepath))
        except yaml.YAMLError as exc:
            errors.append(f"{filepath}: YAML parse error: {exc}")
    return errors


def validate_page_health_resolver(contracts_dir: str) -> list[str]:
    """Validate page_health_resolver.yaml contains the semantic split flags."""
    errors = []
    filepath = os.path.join(contracts_dir, 'page_health_resolver.yaml')

    if not os.path.exists(filepath):
        return []

    data = load_yaml(filepath)
    output = data.get('output', {})
    required = [
        'body_publishable',
        'seo_indexable',
        'claim_publishable',
        'schema_publishable',
        'materialized',
        'fallback_served',
    ]
    for field in required:
        if field not in output:
            errors.append(f"page_health_resolver: missing output field {field}")
    return errors


def validate_cache_materialization(contracts_dir: str) -> list[str]:
    """Validate cache_materialization.yaml declares identity metadata."""
    errors = []
    filepath = os.path.join(contracts_dir, 'cache_materialization.yaml')

    if not os.path.exists(filepath):
        return []

    data = load_yaml(filepath)
    metadata = data.get('required_metadata', {})
    required = [
        'rendered_at',
        'build_id',
        'deploy_id',
        'content_hash',
        'template_family',
        'url',
        'indexable',
        'publishable',
    ]
    for field in required:
        if field not in metadata:
            errors.append(f"cache_materialization: missing required metadata {field}")
    return errors


def validate_claim_decision(contracts_dir: str) -> list[str]:
    """Validate claim_decision.yaml exposes public surface rules."""
    errors = []
    filepath = os.path.join(contracts_dir, 'claim_decision.yaml')

    if not os.path.exists(filepath):
        return []

    data = load_yaml(filepath)
    surfaces = data.get('surfaces', {})
    for surface in ['visible_text', 'structured_data', 'agent_api']:
        if surface not in surfaces:
            errors.append(f"claim_decision: missing surface {surface}")
    return errors


def main():
    parser = argparse.ArgumentParser(description='Validate Constitutional CMS contracts')
    parser.add_argument('--contracts-dir', default='./contracts', help='Path to contracts directory')
    parser.add_argument('--check', choices=[
        'syntax',
        'page_types',
        'enrichment',
        'links',
        'boundary',
        'page_health',
        'cache',
        'claims',
        'all',
    ],
                       default='all', help='Which contract to validate')
    args = parser.parse_args()
    
    contracts_dir = args.contracts_dir
    
    if not os.path.isdir(contracts_dir):
        print(f"ERROR: Contracts directory not found: {contracts_dir}")
        sys.exit(1)
    
    all_errors = []
    
    checks = {
        'syntax': ('YAML Syntax', validate_yaml_syntax),
        'page_types': ('Page Types', validate_page_types),
        'enrichment': ('Enrichment Stages', validate_enrichment_stages),
        'links': ('Link Rules', validate_link_rules),
        'boundary': ('Snapshot Boundary', validate_snapshot_boundary),
        'page_health': ('Page Health Resolver', validate_page_health_resolver),
        'cache': ('Cache Materialization', validate_cache_materialization),
        'claims': ('Claim Decision', validate_claim_decision),
    }
    
    if args.check == 'all':
        run_checks = checks.keys()
    else:
        run_checks = [args.check]
    
    for check_name in run_checks:
        label, validator = checks[check_name]
        print(f"\n{'='*60}")
        print(f"  Validating: {label}")
        print(f"{'='*60}")
        
        errors = validator(contracts_dir)
        
        if errors:
            for error in errors:
                print(f"  ✗ {error}")
            all_errors.extend(errors)
        else:
            print(f"  ✓ All checks passed")
    
    print(f"\n{'='*60}")
    if all_errors:
        print(f"  FAILED: {len(all_errors)} error(s) found")
        sys.exit(1)
    else:
        print(f"  PASSED: All contracts are internally consistent")
        sys.exit(0)


if __name__ == '__main__':
    main()
