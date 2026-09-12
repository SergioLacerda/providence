# Generated Artifacts

Ruleset version: `{{ standalone_ruleset_version }}`
Last verified: `{{ last_verified }}`

Never hand-edit generated or compiled output. If a generated file is wrong, that is a signal that its source is wrong â€” fix the source and regenerate.

A generated file that disagrees with its source is drift, not a merge conflict to resolve in the generated file itself. Treating generated output as editable in place lets the source and the output silently diverge, and the next regeneration will overwrite whatever was hand-patched â€” quietly reintroducing the original problem.

If you are unsure whether a file is generated, look for a header comment naming a generator, or check whether the directory is listed as build output in the project's ignore rules.
