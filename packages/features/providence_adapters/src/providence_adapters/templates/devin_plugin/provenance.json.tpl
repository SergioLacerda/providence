{
  "plugin_version": "{{ plugin_version }}",
  "compiler_version": "{{ compiler_version }}",
  "governance_schema_version": "{{ schema_version }}",
  "source_revision": "{{ source_revision }}",
  "built_at": "{{ built_at }}",
  "embedded_policy_digest": "sha256:{{ policy_digest }}",
  "embedded_governance_summary_digest": "sha256:{{ governance_summary_digest }}",
  "soft_governance_ruleset_version": "{{ soft_governance_ruleset_version }}",
  "coding_practices_digest": {% if has_coding_practices %}"sha256:{{ coding_practices_digest }}"{% else %}null{% endif %},
  "active_policy_digest": null,
  "profile": "soft",
  "provider": "devin",
  "compatibility_relationship": "not_applicable_soft_profile"
}
