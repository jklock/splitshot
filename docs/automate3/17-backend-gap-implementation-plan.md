# Backend Gap Implementation Plan

> **Purpose:** Exact specification for fixing the 6 known backend gaps before or during UI implementation. These gaps were identified in `07-api-and-backend-contract.md`.
>
> **Rule:** The UI must not claim a feature is complete until its backend route is proven with a test.

---

## Gap 1: `/api/workspace/apply-from-first`

### Current Behavior
- Stores metadata snapshot (`first_stage_snapshot`)
- Marks siblings as `inherited_from_first = True`
- Does NOT copy actual project settings from Stage 1 to siblings

### Required Behavior
1. Identify all "reusable settings" from Stage 1's project:
   - Output profile selections
   - Overlay visibility settings
   - Export preset
   - Frame profile (video shape)
   - Metric captions setting
   - Lead-in card setting
   - Brand mark setting
2. For each sibling stage:
   - Load the stage's project
   - Apply Stage 1's reusable settings
   - If sibling has explicit override, skip that setting and mark as conflict
   - Save the sibling's project
3. Return summary: `{ applied: int, skipped: int, conflicts: [{ stage_id, setting, reason }] }`

### Implementation

**File:** `src/splitshot/ui/controller.py`

```python
def workspace_apply_from_first(self, settings: dict | None = None) -> dict:
    """Apply Stage 1 settings to all sibling stages.
    
    Returns:
        dict with applied count, skipped count, and conflict list.
    """
    if not self.workspace:
        return {"error": "No workspace open"}
    
    stage_entries = list(self.workspace.stage_entries.values())
    if len(stage_entries) < 2:
        return {"error": "Need at least 2 stages"}
    
    first_entry = stage_entries[0]
    if not first_entry.stage_id:
        return {"error": "Stage 1 has no stage_id"}
    
    # Load Stage 1 project
    first_project = self._load_stage_project(first_entry.stage_id)
    if not first_project:
        return {"error": f"Cannot load Stage 1 project: {first_entry.stage_id}"}
    
    # Extract reusable settings
    reusable = self._extract_reusable_settings(first_project)
    
    applied = 0
    skipped = 0
    conflicts = []
    
    for entry in stage_entries[1:]:
        if not entry.stage_id:
            continue
        
        sibling_project = self._load_stage_project(entry.stage_id)
        if not sibling_project:
            skipped += 1
            conflicts.append({
                "stage_id": entry.stage_id,
                "setting": "all",
                "reason": "Cannot load project"
            })
            continue
        
        stage_conflicts = []
        for key, value in reusable.items():
            if entry.override_values and key in entry.override_values:
                stage_conflicts.append({
                    "setting": key,
                    "reason": "Stage has explicit override"
                })
                continue
            
            # Apply setting to sibling project
            self._apply_setting_to_project(sibling_project, key, value)
        
        if stage_conflicts:
            conflicts.extend([{**c, "stage_id": entry.stage_id} for c in stage_conflicts])
        
        # Save sibling project
        self._save_stage_project(entry.stage_id, sibling_project)
        entry.inherited_from_first = True
        applied += 1
    
    self.workspace.first_stage_snapshot = {
        "stage_id": first_entry.stage_id,
        "defaults": reusable,
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }
    self.workspace.updated_at = datetime.now(timezone.utc)
    self.autosave_project_if_needed()
    
    return {
        "applied": applied,
        "skipped": skipped,
        "conflicts": conflicts,
        "snapshot": self.workspace.first_stage_snapshot,
    }

def _extract_reusable_settings(self, project: Project) -> dict:
    """Extract settings that can be shared across stages."""
    return {
        "export_preset": project.export.preset.value if project.export.preset else None,
        "overlay_position": project.overlay.position.value if project.overlay.position else None,
        "overlay_badge_size": project.overlay.badge_size.value if project.overlay.badge_size else None,
        "overlay_display_options": {
            "show_timer": project.overlay.display_options.show_timer,
            "show_shots": project.overlay.display_options.show_shots,
            "show_score": project.overlay.display_options.show_score,
        },
        "frame_profile": project.export.frame_profile if hasattr(project.export, 'frame_profile') else None,
    }

def _apply_setting_to_project(self, project: Project, key: str, value: any) -> None:
    """Apply a single setting to a project."""
    if key == "export_preset" and value:
        project.export.preset = ExportPreset(value)
    elif key == "overlay_position" and value:
        project.overlay.position = OverlayPosition(value)
    elif key == "overlay_badge_size" and value:
        project.overlay.badge_size = BadgeSize(value)
    elif key == "overlay_display_options" and value:
        for opt_key, opt_val in value.items():
            setattr(project.overlay.display_options, opt_key, opt_val)
```

**File:** `src/splitshot/browser/server.py`

Update `_handle_workspace_apply_from_first` to call the new controller method.

**Test:**

```python
# tests/browser/test_apply_from_first.py
def test_apply_from_first_copies_settings():
    # Create workspace with 2 stages
    # Set Stage 1 export preset
    # Call apply-from-first
    # Verify Stage 2 has same export preset
    pass

def test_apply_from_first_respects_overrides():
    # Create workspace with 2 stages
    # Set Stage 1 export preset
    # Set Stage 2 override for export preset
    # Call apply-from-first
    # Verify Stage 2 keeps its override
    pass
```

---

## Gap 2: `/api/workspace/apply-from-first/preview`

### Current Behavior
- Returns list of stages with `will_inherit` boolean
- No concrete diff or conflict details

### Required Behavior
1. Load Stage 1 project
2. Extract reusable settings
3. For each sibling:
   - Load sibling project
   - Compare each reusable setting
   - If different and no override → mark as "will_change"
   - If different and has override → mark as "conflict"
   - If same → mark as "unchanged"
4. Return preview with concrete changes

### Implementation

```python
def workspace_apply_from_first_preview(self) -> dict:
    """Preview what would change if apply-from-first is executed."""
    if not self.workspace:
        return {"error": "No workspace open"}
    
    stage_entries = list(self.workspace.stage_entries.values())
    if len(stage_entries) < 2:
        return {"error": "Need at least 2 stages", "preview": []}
    
    first_entry = stage_entries[0]
    first_project = self._load_stage_project(first_entry.stage_id)
    reusable = self._extract_reusable_settings(first_project) if first_project else {}
    
    preview = []
    for entry in stage_entries[1:]:
        if not entry.stage_id:
            continue
        
        sibling_project = self._load_stage_project(entry.stage_id)
        if not sibling_project:
            preview.append({
                "stage_id": entry.stage_id,
                "display_name": entry.display_name or f"Stage {entry.stage_number}",
                "status": "unavailable",
                "reason": "Cannot load project",
                "changes": [],
            })
            continue
        
        changes = []
        conflicts = []
        
        for key, first_value in reusable.items():
            sibling_value = self._get_setting_from_project(sibling_project, key)
            has_override = entry.override_values and key in entry.override_values
            
            if first_value == sibling_value:
                continue  # No change needed
            
            if has_override:
                conflicts.append({
                    "setting": key,
                    "current_value": sibling_value,
                    "proposed_value": first_value,
                    "reason": "Stage has explicit override",
                })
            else:
                changes.append({
                    "setting": key,
                    "current_value": sibling_value,
                    "new_value": first_value,
                })
        
        status = "conflict" if conflicts else ("will_change" if changes else "unchanged")
        
        preview.append({
            "stage_id": entry.stage_id,
            "display_name": entry.display_name or f"Stage {entry.stage_number}",
            "status": status,
            "changes": changes,
            "conflicts": conflicts,
        })
    
    return {
        "preview": preview,
        "source_stage": first_entry.display_name or "Stage 1",
        "reusable_settings": list(reusable.keys()),
    }
```

---

## Gap 3: `/api/library/backup/create`

### Current Behavior
- Returns in-memory manifest JSON
- Does NOT persist to disk

### Required Behavior
1. Generate manifest with all library records
2. Write manifest to `~/.splitshot/library/backups/backup_YYYY-MM-DD_HH-MM-SS.json`
3. Return path and record counts

### Implementation

```python
import json
from datetime import datetime
from pathlib import Path

def _handle_library_backup_create(self) -> dict[str, Any]:
    """Create a persisted backup of the library."""
    from splitshot.persistence.library import read_stage_metrics, read_match_metrics
    
    stages = read_stage_metrics()
    matches = read_match_metrics()
    
    manifest = {
        "backup_id": uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": 1,
        "total_stages": len(stages),
        "total_matches": len(matches),
        "stage_records": stages[-100:],
        "match_records": matches[-50:],
    }
    
    # Persist to disk
    backup_dir = Path.home() / ".splitshot" / "library" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = backup_dir / f"backup_{timestamp}.json"
    backup_path.write_text(json.dumps(manifest, indent=2))
    
    return {
        "manifest": manifest,
        "backup_path": str(backup_path),
        "message": f"Backup created with {len(stages)} stages and {len(matches)} matches at {backup_path}",
    }
```

---

## Gap 4: `/api/library/backup/restore`

### Current Behavior
- Accepts manifest
- Returns counts
- Does NOT write to library store

### Required Behavior
1. Validate manifest schema version
2. Write stage records to `library/records/stages/`
3. Write match records to `library/records/matches/`
4. Append metrics to JSONL files
5. Return restored counts

### Implementation

```python
def _handle_library_backup_restore(self, body: dict[str, Any]) -> dict[str, Any]:
    """Restore library from a persisted backup manifest."""
    manifest = (body or {}).get("manifest", {})
    if not manifest:
        return {"error": "No backup manifest provided"}
    
    schema_version = manifest.get("schema_version", 0)
    if schema_version != 1:
        return {"error": f"Unsupported schema version: {schema_version}"}
    
    from splitshot.persistence.library import (
        save_stage_record,
        save_match_record,
        append_stage_metric,
        append_match_metric,
    )
    from splitshot.domain.models import LibraryStageRecord, LibraryMatchRecord
    
    restored_stages = 0
    restored_matches = 0
    
    for stage_data in manifest.get("stage_records", []):
        try:
            record = LibraryStageRecord(**stage_data)
            save_stage_record(record)
            append_stage_metric(_record_to_dict(record))
            restored_stages += 1
        except Exception as e:
            pass  # Log and continue
    
    for match_data in manifest.get("match_records", []):
        try:
            record = LibraryMatchRecord(**match_data)
            save_match_record(record)
            append_match_metric(_record_to_dict(record))
            restored_matches += 1
        except Exception as e:
            pass
    
    return {
        "restored": True,
        "stages_restored": restored_stages,
        "matches_restored": restored_matches,
        "message": f"Restored {restored_stages} stages and {restored_matches} matches",
    }
```

---

## Gap 5: `/api/landing/recent`

### Current Behavior
- Scans `~/.splitshot/projects`
- Returns only stage project directories
- Does NOT return Match or Library records

### Required Behavior
1. Continue returning stage projects
2. Also scan workspaces and return recent matches
3. Also scan library records and return recent stages/matches
4. Return mixed list sorted by date

### Implementation

```python
def _handle_landing_recent(self) -> dict[str, Any]:
    """Return recent activity: stages, matches, and library records."""
    from pathlib import Path as _Path
    from datetime import datetime
    
    recent = []
    
    # Stage projects (existing logic)
    try:
        library_root = _Path.home() / ".splitshot" / "projects"
        if library_root.is_dir():
            for candidate in library_root.iterdir():
                if candidate.is_dir():
                    meta_path = candidate / "project.json"
                    if meta_path.is_file():
                        try:
                            import json as _json
                            data = _json.loads(meta_path.read_text())
                            recent.append({
                                "name": data.get("name", candidate.name),
                                "path": str(candidate),
                                "date": data.get("last_opened", "") or data.get("modified_at", ""),
                                "type": "stage",
                                "surface": "single",
                            })
                        except Exception:
                            pass
    except Exception:
        pass
    
    # Workspaces (matches)
    try:
        workspace_root = _Path.home() / ".splitshot" / "workspaces"
        if workspace_root.is_dir():
            for candidate in workspace_root.iterdir():
                if candidate.is_dir():
                    meta_path = candidate / "workspace.json"
                    if meta_path.is_file():
                        try:
                            import json as _json
                            data = _json.loads(meta_path.read_text())
                            recent.append({
                                "name": data.get("name", candidate.name),
                                "path": str(candidate),
                                "date": data.get("modified_at", ""),
                                "type": "match",
                                "surface": "multi",
                            })
                        except Exception:
                            pass
    except Exception:
        pass
    
    # Library records
    try:
        from splitshot.persistence.library import read_stage_metrics, read_match_metrics
        for stage in read_stage_metrics()[-5:]:
            recent.append({
                "name": stage.get("display_name", "Untitled"),
                "path": stage.get("project_path", ""),
                "date": stage.get("event_date", ""),
                "type": "stage",
                "surface": "single",
                "library_record_id": stage.get("library_record_id", ""),
            })
        for match in read_match_metrics()[-3:]:
            recent.append({
                "name": match.get("display_name", "Untitled Match"),
                "path": "",
                "date": match.get("event_date", ""),
                "type": "match",
                "surface": "multi",
                "library_record_id": match.get("library_record_id", ""),
            })
    except Exception:
        pass
    
    # Sort by date descending
    recent.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    return {"recent": recent[:15]}
```

---

## Gap 6: `ProjectController.proxy_refresh` Empty Output ID

### Current Behavior
- Calls `output_profile_render("")` with empty string
- This is suspicious and may fail

### Required Behavior
1. If output_id is empty, use a default proxy output profile
2. Or generate a minimal render plan directly

### Implementation

```python
def proxy_refresh(self, scope_type: str = "stage", scope_id: str | None = None) -> dict:
    """Request proxy regeneration."""
    sid = scope_id or self.project.id
    
    if scope_type == "stage" and not self.project.primary_video.path:
        return {"status": "no_media", "message": "No primary video available"}
    
    current_hash = (
        self._compute_truth_hash()
        if scope_type == "stage"
        else self._compute_workspace_truth_hash()
    )
    
    # FIX: Generate a default render plan if no output profile specified
    try:
        render_plan = self._generate_default_render_plan(scope_type)
    except Exception:
        render_plan = None
    
    # ... rest of existing logic ...

def _generate_default_render_plan(self, scope_type: str) -> dict:
    """Generate a minimal default render plan for proxy generation."""
    return {
        "steps": ["source_copy", "proxy_encode"],
        "estimated_duration_ms": 0,
        "output_path": "",
        "dimensions": {"width": 1920, "height": 1080},
        "frame_rate": "30",
        "has_warnings": False,
        "warnings": [],
    }
```

---

## Implementation Priority

1. **Gap 6** (proxy_refresh) — Lowest risk, fixes existing bug
2. **Gap 5** (landing recent) — Medium risk, extends existing route
3. **Gap 1 & 2** (apply-from-first) — High risk, requires project loading logic; implement preview before apply
4. **Gap 3 & 4** (backup) — Lowest priority; label UI as "Export Manifest" if not implemented

---

## Verification Checklist

For each gap fix:
- [ ] Controller method updated or added
- [ ] Route handler updated in `server.py`
- [ ] Narrow Python test exercises the new behavior
- [ ] Test passes: `uv run pytest tests/browser/`
- [ ] UI control can be wired and tested
