# F.S.A. → EGM4000 Exact Telemetry Bridge

F.S.A. remains a separate product/codebase. EGM4000 only ingests exact telemetry when the operator explicitly configures a bridge key.

Set `EGM_FSA_BRIDGE_KEY` on the EGM4000 full-stack server. The separate F.S.A. service sends an authenticated POST to the telemetry bridge with a user/session identifier and events.

Accepted bridge events are stored as `evidence_type = exact_telemetry`, `confidence = 1`, and an exact F.S.A. source label. Duplicate source event IDs are ignored.

If no bridge key is configured, the bridge must report `bridge_not_configured`. EGM4000 must never pretend exact telemetry is active when it is not.
