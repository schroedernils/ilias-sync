# Isolated changes/readability comparison (issue #2)

This is a **synthetic prototype**, outside the production archive and native package. It uses its own temporary SQLite
ledger and fixture files; no real source, account, schedule, cache or course material is loaded. It is a German-language
owner/agent review surface, not a validated new product workflow. No study with other people is required or performed.

```sh
.venv/bin/python scripts/prototype_changes.py
QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/prototype_changes.py --render .local/changes-prototype-review
```

The existing material-table widget compares **since your overview**, a seven-day chronology and all materials. Only the
unfiltered overview permits acknowledgement, so hidden search/date results are not silently acknowledged. The captured
event-ID boundary survives equal timestamps, clock rollback, restart and a new update during review. Undo restores the
previous checkpoint. Merely opening the app/file does not acknowledge anything. A baseline, unchanged bytes, path-only
changes, restored copies and generated information do not generate teaching-material events. Different IDs remain
separate even with the same digest. The prototype retains events; no automatic destructive compaction is implemented.

The explicit local read check reads the whole ordinary fixture file, checks stable file identity/stat information,
separates missing/unreadable/link/root-unavailable cases, and rejects recognized cloud paths and symlinks/junctions
including the selected root and its ancestors. It never repairs, writes, hydrates known cloud placeholders or scans
continuously. Its UI has no free folder picker. This is deliberately **not a general cloud-residency or mount detector**:
`local_read_passed` is a timestamped fixture read, not proof that a provider-backed file can open offline. Every result
keeps `offline_certified=False`. General user-selected roots require additional provider/mount validation before any
production integration; no offline-assurance badge is shipped.

Seven deterministic model/boundary tests and six rendered UI scenarios cover overview → acknowledge → new update →
undo → explicit read check → date range. These are agent/engineering checks, not participant times or evidence of demand.
The existing production preservation/version tests remain separate. Before connecting this to publication, decide with
Nils whether checkpoints reduce effort compared with the existing chronological library; define baseline/migration,
retention and the exact supported local-storage boundary. Physical offline document opening is not certified here.
