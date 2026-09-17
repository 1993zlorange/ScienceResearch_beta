"""PostgreSQL baseline for ScienceResearch SQLite schema v6.

Revision ID: 0001_postgres_baseline_v6
Revises:
Create Date: 2026-09-14

This migration establishes the approved full PostgreSQL structure. It does not
import or transform source SQLite data.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_postgres_baseline_v6"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE achievement_file_outbox (
	id VARCHAR(128), 
	operation TEXT NOT NULL, 
	relative_path TEXT NOT NULL, 
	status VARCHAR(64) NOT NULL, 
	error TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
)"""
    )

    op.execute(
        """CREATE TABLE apply_journal (
	id VARCHAR(128), 
	demand_id VARCHAR(128) NOT NULL, 
	documents_json JSONB NOT NULL, 
	status VARCHAR(64) NOT NULL, 
	error TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)"""
    )

    op.execute(
        """CREATE TABLE artifacts (
	id VARCHAR(128), 
	item_id VARCHAR(128), 
	wp_id VARCHAR(128) NOT NULL, 
	kind VARCHAR(64) NOT NULL, 
	name TEXT NOT NULL, 
	payload JSONB NOT NULL, 
	status VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	context_id VARCHAR(128), 
	workflow_id VARCHAR(128), 
	run_id VARCHAR(128), 
	catalog_version TEXT, 
	step_no INTEGER, 
	PRIMARY KEY (id)
)"""
    )

    op.execute(
        """CREATE TABLE attachment_path_migrations (
	migration_id VARCHAR(128), 
	scope_json JSONB NOT NULL, 
	dry_run BOOLEAN NOT NULL, 
	state VARCHAR(64) NOT NULL, 
	plan_digest TEXT NOT NULL, 
	error TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	row_version INTEGER DEFAULT 1 NOT NULL, 
	idempotency_key TEXT, 
	resolved_context_id VARCHAR(128), 
	execution_idempotency_key TEXT, 
	execution_result_json JSONB, 
	execution_operation TEXT, 
	execution_request_digest TEXT, 
	PRIMARY KEY (migration_id), 
	UNIQUE (idempotency_key), 
	CHECK (state IN ('PLANNED','RUNNING','COMPLETED','PARTIAL','INTERRUPTED','CLEANUP_PENDING'))
)"""
    )

    op.execute(
        """CREATE TABLE composite_skills (
	id VARCHAR(128), 
	wp_id VARCHAR(128) NOT NULL, 
	version TEXT NOT NULL, 
	payload JSONB NOT NULL, 
	status VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (wp_id, version)
)"""
    )

    op.execute(
        """CREATE TABLE context_deletion_operations (
	operation_id VARCHAR(128), 
	context_id VARCHAR(128) NOT NULL, 
	context_version INTEGER NOT NULL, 
	retain_files BOOLEAN NOT NULL, 
	state VARCHAR(64) NOT NULL, 
	manifest_ref TEXT, 
	trash_ref TEXT, 
	error TEXT, 
	idempotency_key TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	row_version INTEGER DEFAULT 1 NOT NULL, 
	confirmation_expires_at TIMESTAMP WITH TIME ZONE, 
	confirmation_consumed_at TIMESTAMP WITH TIME ZONE, 
	confirmation_nonce_hash TEXT, 
	request_id VARCHAR(128), 
	session_id VARCHAR(128), 
	entity_counts_json JSONB, 
	file_manifest_json JSONB, 
	manifest_digest TEXT, 
	archive_relative_path TEXT, 
	trash_relative_path TEXT, 
	error_code TEXT, 
	error_detail TEXT, 
	PRIMARY KEY (operation_id), 
	CHECK (state IN ('PREPARED','FILES_STAGED','DB_COMMITTED','FILE_MOVED','DONE','CLEANUP_PENDING','ROLLED_BACK','FAILED')), 
	UNIQUE (idempotency_key)
)"""
    )

    op.execute(
        """CREATE TABLE contexts (
	id VARCHAR(128), 
	type VARCHAR(64) NOT NULL, 
	name TEXT NOT NULL, 
	problem TEXT NOT NULL, 
	goal TEXT NOT NULL, 
	owner TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	row_version INTEGER DEFAULT 1 NOT NULL, 
	lifecycle_state TEXT DEFAULT 'Active' NOT NULL, 
	PRIMARY KEY (id)
)"""
    )

    op.execute(
        """CREATE TABLE deleted_context_archives (
	archive_id VARCHAR(128), 
	operation_id VARCHAR(128) NOT NULL, 
	context_id VARCHAR(128) NOT NULL, 
	manifest_relative_path TEXT NOT NULL, 
	attachment_count INTEGER DEFAULT 0 NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	content_digest TEXT NOT NULL, 
	PRIMARY KEY (archive_id), 
	UNIQUE (operation_id)
)"""
    )

    op.execute(
        """CREATE TABLE document_candidates (
	id VARCHAR(128), 
	demand_id VARCHAR(128) NOT NULL, 
	kind VARCHAR(64) NOT NULL, 
	payload JSONB NOT NULL, 
	status VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)"""
    )

    op.execute(
        """CREATE TABLE governance (
	id VARCHAR(128), 
	kind VARCHAR(64) NOT NULL, 
	payload JSONB NOT NULL, 
	status VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)"""
    )

    op.execute(
        """CREATE TABLE log_imports (
	id VARCHAR(128), 
	root TEXT NOT NULL, 
	date_from TEXT, 
	date_to TEXT, 
	events_json JSONB NOT NULL, 
	warnings_json JSONB NOT NULL, 
	image_candidates_json JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)"""
    )

    op.execute(
        """CREATE TABLE manual_skill_events (
	id VARCHAR(128), 
	run_id VARCHAR(128) NOT NULL, 
	step_no INTEGER, 
	event VARCHAR(64) NOT NULL, 
	payload JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)"""
    )

    op.execute(
        """CREATE TABLE manual_skill_runs (
	id VARCHAR(128), 
	wp_id VARCHAR(128) NOT NULL, 
	context_id VARCHAR(128), 
	workflow_id VARCHAR(128), 
	inputs_json JSONB NOT NULL, 
	state VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	item_id VARCHAR(128), 
	PRIMARY KEY (id)
)"""
    )

    op.execute(
        """CREATE TABLE manual_skill_steps (
	id VARCHAR(128), 
	run_id VARCHAR(128) NOT NULL, 
	step_no INTEGER NOT NULL, 
	instruction TEXT NOT NULL, 
	state VARCHAR(64) NOT NULL, 
	artifact_id VARCHAR(128), 
	detail TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)"""
    )

    op.execute(
        """CREATE TABLE operation_audit_events (
	operation_id VARCHAR(128), 
	request_id VARCHAR(128) NOT NULL, 
	idempotency_key TEXT NOT NULL, 
	context_id VARCHAR(128), 
	actor TEXT NOT NULL, 
	display_label TEXT NOT NULL, 
	action VARCHAR(64) NOT NULL, 
	target_type TEXT NOT NULL, 
	target_id VARCHAR(128) NOT NULL, 
	result VARCHAR(64) NOT NULL, 
	error_code TEXT, 
	summary TEXT DEFAULT '' NOT NULL, 
	summary_json JSONB DEFAULT '{}'::jsonb NOT NULL, 
	schema_version INTEGER DEFAULT 4 NOT NULL, 
	occurred_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	content_digest TEXT NOT NULL, 
	PRIMARY KEY (operation_id), 
	CHECK (result IN ('SUCCESS','REJECTED','FAILED','PENDING','CLEANUP_PENDING')), 
	UNIQUE (idempotency_key)
)"""
    )

    op.execute(
        """CREATE INDEX ix_operation_audit_action_result ON operation_audit_events (action, result, occurred_at DESC)"""
    )

    op.execute(
        """CREATE INDEX ix_operation_audit_context_time ON operation_audit_events (context_id, occurred_at DESC, operation_id DESC)"""
    )

    op.execute("""CREATE INDEX ix_operation_audit_request ON operation_audit_events (request_id, occurred_at DESC)""")

    op.execute(
        """CREATE INDEX ix_operation_audit_target ON operation_audit_events (target_type, target_id, occurred_at DESC)"""
    )

    op.execute(
        """CREATE TABLE operation_audit_outbox (
	outbox_id VARCHAR(128), 
	migration_id VARCHAR(128), 
	payload_json JSONB NOT NULL, 
	status VARCHAR(64) NOT NULL, 
	error TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	operation TEXT, 
	action VARCHAR(64), 
	target_type TEXT, 
	target_id VARCHAR(128), 
	idempotency_key TEXT, 
	attempts INTEGER DEFAULT 0 NOT NULL, 
	lease_token TEXT, 
	next_retry_at TIMESTAMP WITH TIME ZONE, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (outbox_id), 
	CHECK (status IN ('PENDING','DONE','FAILED'))
)"""
    )

    op.execute(
        """CREATE INDEX ix_operation_audit_outbox_status_retry ON operation_audit_outbox (status, next_retry_at, updated_at)"""
    )

    op.execute(
        """CREATE TABLE operations_configuration_history (
	history_id VARCHAR(128), 
	config_id VARCHAR(128) NOT NULL, 
	version INTEGER NOT NULL, 
	payload_json JSONB NOT NULL, 
	changed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	changed_by TEXT NOT NULL, 
	PRIMARY KEY (history_id)
)"""
    )

    op.execute(
        """CREATE TABLE operations_configurations (
	config_id VARCHAR(128), 
	version INTEGER NOT NULL, 
	payload_json JSONB NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_by TEXT NOT NULL, 
	PRIMARY KEY (config_id), 
	CHECK (version >= 1), 
	CHECK (config_id IN ('model_profile'))
)"""
    )

    op.execute(
        """CREATE TABLE projection_outbox (
	id VARCHAR(128), 
	filename TEXT NOT NULL, 
	record_json JSONB NOT NULL, 
	projection_hash TEXT NOT NULL, 
	status VARCHAR(64) NOT NULL, 
	attempts INTEGER DEFAULT 0 NOT NULL, 
	error TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	projected_at TIMESTAMP WITH TIME ZONE, 
	expected_base_hash TEXT, 
	projected_file_hash TEXT, 
	event_hash TEXT, 
	PRIMARY KEY (id), 
	UNIQUE (projection_hash)
)"""
    )

    op.execute(
        """CREATE TABLE report_confirmations (
	id VARCHAR(128), 
	week_id VARCHAR(128) NOT NULL, 
	model_json JSONB NOT NULL, 
	input_hash TEXT NOT NULL, 
	author TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (week_id, input_hash)
)"""
    )

    op.execute(
        """CREATE TABLE schema_migrations (
	migration_id VARCHAR(128), 
	version INTEGER NOT NULL, 
	name TEXT NOT NULL, 
	attempt INTEGER NOT NULL, 
	checksum TEXT NOT NULL, 
	state VARCHAR(64) NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	applied_at TIMESTAMP WITH TIME ZONE, 
	error TEXT, 
	backup_ref TEXT, 
	request_id VARCHAR(128), 
	PRIMARY KEY (migration_id), 
	CHECK (attempt >= 1), 
	CHECK ((state='APPLIED' AND applied_at IS NOT NULL) OR
                          (state IN ('STARTED','FAILED') AND applied_at IS NULL)), 
	CHECK (state IN ('STARTED','APPLIED','FAILED'))
)"""
    )

    op.execute("""CREATE INDEX ix_schema_migrations_state ON schema_migrations (state, version)""")

    op.execute("""CREATE INDEX ix_schema_migrations_version_state ON schema_migrations (version, state)""")

    op.execute(
        """CREATE UNIQUE INDEX ux_schema_migrations_applied_version ON schema_migrations (version) WHERE state = 'APPLIED'"""
    )

    op.execute(
        """CREATE TABLE skills (
	id VARCHAR(128), 
	manifest JSONB NOT NULL, 
	manifest_hash TEXT NOT NULL, 
	status VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)"""
    )

    op.execute(
        """CREATE TABLE templates (
	id VARCHAR(128), 
	wp_id VARCHAR(128) NOT NULL, 
	version TEXT NOT NULL, 
	payload JSONB NOT NULL, 
	status VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (wp_id, version)
)"""
    )

    op.execute(
        """CREATE TABLE ui_sessions (
	id VARCHAR(128), 
	nonce_hash TEXT NOT NULL, 
	expires_at FLOAT NOT NULL, 
	revoked_at FLOAT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	token_hash TEXT, 
	actor TEXT, 
	display_label TEXT, 
	PRIMARY KEY (id)
)"""
    )

    op.execute(
        """CREATE UNIQUE INDEX ux_ui_sessions_token_hash ON ui_sessions (token_hash) WHERE token_hash IS NOT NULL AND token_hash <> ''"""
    )

    op.execute(
        """CREATE TABLE upload_settings (
	id SERIAL, 
	max_file_bytes BIGINT NOT NULL, 
	max_attachments_per_card INTEGER NOT NULL, 
	allowed_extensions JSONB NOT NULL, 
	version INTEGER DEFAULT 1 NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	actor TEXT DEFAULT 'system' NOT NULL, 
	effective_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CHECK (id=1), 
	CONSTRAINT ck_upload_settings_singleton CHECK (id = 1)
)"""
    )

    op.execute(
        """CREATE TABLE upload_settings_history (
	id VARCHAR(128), 
	version INTEGER NOT NULL, 
	max_file_bytes BIGINT NOT NULL, 
	max_attachments_per_card INTEGER NOT NULL, 
	allowed_extensions JSONB NOT NULL, 
	active BOOLEAN DEFAULT false NOT NULL, 
	actor TEXT NOT NULL, 
	effective_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (version)
)"""
    )

    op.execute(
        """CREATE TABLE weeks (
	id VARCHAR(128), 
	week_start TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (week_start)
)"""
    )

    op.execute(
        """CREATE TABLE workflow_completion_events (
	id VARCHAR(128), 
	workflow_id VARCHAR(128) NOT NULL, 
	actor TEXT NOT NULL, 
	from_status TEXT NOT NULL, 
	to_status TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	context_id VARCHAR(128), 
	work_package_id VARCHAR(128), 
	row_version INTEGER DEFAULT 1 NOT NULL, 
	actor_kind TEXT DEFAULT 'human_user' NOT NULL, 
	version_before INTEGER DEFAULT 0 NOT NULL, 
	version_after INTEGER DEFAULT 0 NOT NULL, 
	idempotency_key TEXT, 
	authorization_source TEXT, 
	nonce_id VARCHAR(128), 
	nonce_hash TEXT, 
	operation TEXT, 
	authorization_expires_at FLOAT, 
	display_label TEXT, 
	PRIMARY KEY (id)
)"""
    )

    op.execute(
        """CREATE TABLE workflow_events (
	id VARCHAR(128), 
	workflow_id VARCHAR(128) NOT NULL, 
	command VARCHAR(64) NOT NULL, 
	payload JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)"""
    )

    op.execute(
        """CREATE TABLE attachment_path_migration_items (
	item_id VARCHAR(128), 
	migration_id VARCHAR(128) NOT NULL, 
	attachment_id VARCHAR(128) NOT NULL, 
	source_path TEXT NOT NULL, 
	target_path TEXT NOT NULL, 
	source_size BIGINT NOT NULL, 
	source_sha256 TEXT NOT NULL, 
	state VARCHAR(64) NOT NULL, 
	error TEXT, 
	attempts INTEGER DEFAULT 0 NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	row_version INTEGER DEFAULT 1 NOT NULL, 
	staging_path TEXT, 
	before_size BIGINT, 
	before_sha256 TEXT, 
	after_size BIGINT, 
	after_sha256 TEXT, 
	classification VARCHAR(64) DEFAULT 'READY' NOT NULL, 
	PRIMARY KEY (item_id), 
	CHECK (state IN ('PLANNED','RUNNING','MOVED','SKIPPED','FAILED','INTERRUPTED','CLEANUP_PENDING')), 
	UNIQUE (migration_id, attachment_id), 
	CHECK (classification IN ('READY','CONFLICT','MISSING')), 
	FOREIGN KEY(migration_id) REFERENCES attachment_path_migrations (migration_id) ON DELETE CASCADE
)"""
    )

    op.execute(
        """CREATE INDEX ix_attachment_path_migration_items_migration ON attachment_path_migration_items (migration_id, state)"""
    )

    op.execute(
        """CREATE UNIQUE INDEX ux_active_attachment_migration ON attachment_path_migration_items (attachment_id) WHERE state IN ('PLANNED', 'RUNNING', 'INTERRUPTED', 'CLEANUP_PENDING')"""
    )

    op.execute(
        """CREATE TABLE context_area_view_preferences (
	local_user_key TEXT NOT NULL, 
	context_id VARCHAR(128) NOT NULL, 
	area_id VARCHAR(128) NOT NULL, 
	is_expanded BOOLEAN DEFAULT false NOT NULL, 
	row_version INTEGER DEFAULT 1 NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (local_user_key, context_id, area_id), 
	FOREIGN KEY(context_id) REFERENCES contexts (id) ON DELETE CASCADE
)"""
    )

    op.execute("""CREATE INDEX ix_context_area_preferences ON context_area_view_preferences (context_id, area_id)""")

    op.execute(
        """CREATE TABLE context_disclosure_preferences (
	local_user_key TEXT NOT NULL, 
	context_id VARCHAR(128) NOT NULL, 
	disclosure_kind TEXT NOT NULL, 
	stable_subject_id VARCHAR(128) NOT NULL, 
	is_expanded BOOLEAN NOT NULL, 
	row_version INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (local_user_key, context_id, disclosure_kind, stable_subject_id), 
	FOREIGN KEY(context_id) REFERENCES contexts (id) ON DELETE CASCADE, 
	CHECK (disclosure_kind IN ('area','progress','work_package','card','directory')), 
	CHECK (row_version >= 1)
)"""
    )

    op.execute(
        """CREATE INDEX ix_context_disclosure_preferences ON context_disclosure_preferences (context_id, local_user_key, disclosure_kind, stable_subject_id)"""
    )

    op.execute(
        """CREATE TABLE projection_failures (
	id VARCHAR(128), 
	outbox_id VARCHAR(128) NOT NULL, 
	error TEXT NOT NULL, 
	attempts INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(outbox_id) REFERENCES projection_outbox (id)
)"""
    )

    op.execute(
        """CREATE TABLE reports (
	id VARCHAR(128), 
	week_id VARCHAR(128) NOT NULL, 
	kind VARCHAR(64) NOT NULL, 
	input_hash TEXT NOT NULL, 
	output_hash TEXT NOT NULL, 
	template_version TEXT NOT NULL, 
	output TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(week_id) REFERENCES weeks (id)
)"""
    )

    op.execute(
        """CREATE TABLE skill_runs (
	id VARCHAR(128), 
	skill_id VARCHAR(128) NOT NULL, 
	input_json JSONB NOT NULL, 
	state VARCHAR(64) NOT NULL, 
	idempotency_key TEXT NOT NULL, 
	approval_json JSONB, 
	staging TEXT NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	error_code TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(skill_id) REFERENCES skills (id), 
	UNIQUE (idempotency_key)
)"""
    )

    op.execute(
        """CREATE TABLE ui_nonces (
	id VARCHAR(128), 
	session_id VARCHAR(128) NOT NULL, 
	workflow_id VARCHAR(128) NOT NULL, 
	expected_version TEXT NOT NULL, 
	operation TEXT NOT NULL, 
	nonce_hash TEXT NOT NULL, 
	expires_at FLOAT NOT NULL, 
	used_at FLOAT, 
	context_id VARCHAR(128), 
	work_package_id VARCHAR(128), 
	issued_at FLOAT, 
	consume_request_id VARCHAR(128), 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES ui_sessions (id), 
	CONSTRAINT ck_ui_nonces_operation CHECK (operation IN ('complete', 'cancel'))
)"""
    )

    op.execute(
        """CREATE INDEX ix_ui_nonces_binding ON ui_nonces (session_id, workflow_id, expected_version, operation, expires_at, used_at)"""
    )

    op.execute("""CREATE UNIQUE INDEX ux_ui_nonces_hash ON ui_nonces (nonce_hash)""")

    op.execute(
        """CREATE TABLE week_items (
	id VARCHAR(128), 
	week_id VARCHAR(128) NOT NULL, 
	wp_id VARCHAR(128) NOT NULL, 
	title TEXT NOT NULL, 
	deliverable TEXT NOT NULL, 
	relation TEXT, 
	status VARCHAR(64) NOT NULL, 
	row_version INTEGER DEFAULT 1 NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(week_id) REFERENCES weeks (id)
)"""
    )

    op.execute(
        """CREATE TABLE workflows (
	id VARCHAR(128), 
	context_id VARCHAR(128) NOT NULL, 
	work_package_id VARCHAR(128) NOT NULL, 
	status VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	is_completed BOOLEAN DEFAULT false NOT NULL, 
	completion_row_version INTEGER DEFAULT 0 NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	completed_by TEXT, 
	area_id VARCHAR(128), 
	template_id VARCHAR(128), 
	skill_id VARCHAR(128), 
	selection_status TEXT DEFAULT 'Active' NOT NULL, 
	selection_reason TEXT, 
	author_confirmed BOOLEAN DEFAULT false NOT NULL, 
	mode VARCHAR(64) DEFAULT 'human' NOT NULL, 
	row_version INTEGER DEFAULT 1 NOT NULL, 
	archived BOOLEAN DEFAULT false NOT NULL, 
	inputs_json JSONB DEFAULT '{}'::jsonb NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(context_id) REFERENCES contexts (id)
)"""
    )

    op.execute(
        """CREATE TABLE achievement_cards (
	id VARCHAR(128), 
	context_id VARCHAR(128) NOT NULL, 
	workflow_id VARCHAR(128) NOT NULL, 
	work_package_id VARCHAR(128) NOT NULL, 
	event_date TEXT NOT NULL, 
	event_name TEXT NOT NULL, 
	description TEXT DEFAULT '' NOT NULL, 
	status VARCHAR(64) DEFAULT 'Active' NOT NULL, 
	row_version INTEGER DEFAULT 1 NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	week_item_id VARCHAR(128), 
	is_important BOOLEAN DEFAULT false NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workflow_id) REFERENCES workflows (id), 
	FOREIGN KEY(context_id) REFERENCES contexts (id)
)"""
    )

    op.execute(
        """CREATE INDEX ix_cards_context_important_order ON achievement_cards (context_id, is_important, event_date DESC, created_at DESC)"""
    )

    op.execute(
        """CREATE TABLE events (
	id VARCHAR(128), 
	item_id VARCHAR(128) NOT NULL, 
	kind VARCHAR(64) NOT NULL, 
	payload JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(item_id) REFERENCES week_items (id)
)"""
    )

    op.execute(
        """CREATE TABLE evidence (
	id VARCHAR(128), 
	item_id VARCHAR(128) NOT NULL, 
	name TEXT NOT NULL, 
	kind VARCHAR(64) NOT NULL, 
	path TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	sha256 TEXT, 
	source TEXT, 
	stage TEXT, 
	author_confirmed BOOLEAN DEFAULT false NOT NULL, 
	validity VARCHAR(64) DEFAULT 'Valid' NOT NULL, 
	captured_sha256 TEXT, 
	current_sha256 TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(item_id) REFERENCES week_items (id)
)"""
    )

    op.execute(
        """CREATE TABLE gates (
	item_id VARCHAR(128) NOT NULL, 
	gate_key TEXT NOT NULL, 
	passed BOOLEAN NOT NULL, 
	PRIMARY KEY (item_id, gate_key), 
	FOREIGN KEY(item_id) REFERENCES week_items (id)
)"""
    )

    op.execute(
        """CREATE TABLE recommendations (
	id VARCHAR(128), 
	item_id VARCHAR(128) NOT NULL, 
	kind VARCHAR(64) NOT NULL, 
	payload JSONB NOT NULL, 
	status VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(item_id) REFERENCES week_items (id)
)"""
    )

    op.execute(
        """CREATE TABLE skill_events (
	id VARCHAR(128), 
	run_id VARCHAR(128) NOT NULL, 
	state VARCHAR(64) NOT NULL, 
	detail TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES skill_runs (id)
)"""
    )

    op.execute(
        """CREATE TABLE achievement_attachments (
	id VARCHAR(128), 
	card_id VARCHAR(128) NOT NULL, 
	original_name TEXT NOT NULL, 
	storage_name TEXT NOT NULL, 
	relative_path TEXT NOT NULL, 
	mime_type TEXT NOT NULL, 
	size_bytes BIGINT NOT NULL, 
	sha256 TEXT NOT NULL, 
	preview_state TEXT DEFAULT 'available' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	preview_error TEXT, 
	settings_version INTEGER DEFAULT 1 NOT NULL, 
	row_version INTEGER DEFAULT 1 NOT NULL, 
	path_schema_version INTEGER DEFAULT 1 NOT NULL, 
	original_name_key TEXT, 
	area_name_snapshot TEXT, 
	work_package_name_snapshot TEXT, 
	event_folder_snapshot TEXT, 
	before_size_bytes BIGINT, 
	before_sha256 TEXT, 
	after_size_bytes BIGINT, 
	after_sha256 TEXT, 
	staging_path TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(card_id) REFERENCES achievement_cards (id) ON DELETE CASCADE
)"""
    )

    op.execute(
        """CREATE UNIQUE INDEX ux_achievement_attachments_card_name ON achievement_attachments (card_id, lower(original_name))"""
    )

    op.execute(
        """CREATE TABLE achievement_card_events (
	id VARCHAR(128), 
	card_id VARCHAR(128) NOT NULL, 
	actor TEXT NOT NULL, 
	command VARCHAR(64) NOT NULL, 
	payload JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	context_id VARCHAR(128), 
	workflow_id VARCHAR(128), 
	work_package_id VARCHAR(128), 
	week_item_id VARCHAR(128), 
	attachment_id VARCHAR(128), 
	event_type TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(card_id) REFERENCES achievement_cards (id) ON DELETE CASCADE
)"""
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION scienceresearch_block_schema_migrations_update()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'schema migration ledger is immutable';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER schema_migrations_immutable_update
        BEFORE UPDATE ON schema_migrations
        FOR EACH ROW EXECUTE FUNCTION scienceresearch_block_schema_migrations_update()
        """
    )
    op.execute(
        """
        CREATE TRIGGER schema_migrations_immutable_delete
        BEFORE DELETE ON schema_migrations
        FOR EACH ROW EXECUTE FUNCTION scienceresearch_block_schema_migrations_update()
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION scienceresearch_block_operation_audit_update()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'operation audit is immutable';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER operation_audit_immutable_update
        BEFORE UPDATE ON operation_audit_events
        FOR EACH ROW EXECUTE FUNCTION scienceresearch_block_operation_audit_update()
        """
    )
    op.execute(
        """
        CREATE TRIGGER operation_audit_immutable_delete
        BEFORE DELETE ON operation_audit_events
        FOR EACH ROW EXECUTE FUNCTION scienceresearch_block_operation_audit_update()
        """
    )


def downgrade() -> None:
    # The baseline downgrade is intended for isolated PostgreSQL environments.
    # Production rollback requires a reviewed data-preservation decision.
    op.execute(sa.text("DROP TRIGGER IF EXISTS operation_audit_immutable_delete ON operation_audit_events"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS operation_audit_immutable_update ON operation_audit_events"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS scienceresearch_block_operation_audit_update()"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS schema_migrations_immutable_delete ON schema_migrations"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS schema_migrations_immutable_update ON schema_migrations"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS scienceresearch_block_schema_migrations_update()"))
    op.execute(sa.text("DROP TABLE IF EXISTS achievement_card_events CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS achievement_attachments CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS skill_events CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS recommendations CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS gates CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS evidence CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS events CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS achievement_cards CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS workflows CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS week_items CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS ui_nonces CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS skill_runs CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS reports CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS projection_failures CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS context_disclosure_preferences CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS context_area_view_preferences CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS attachment_path_migration_items CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS workflow_events CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS workflow_completion_events CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS weeks CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS upload_settings_history CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS upload_settings CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS ui_sessions CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS templates CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS skills CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS schema_migrations CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS report_confirmations CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS projection_outbox CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS operations_configurations CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS operations_configuration_history CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS operation_audit_outbox CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS operation_audit_events CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS manual_skill_steps CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS manual_skill_runs CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS manual_skill_events CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS log_imports CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS governance CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS document_candidates CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS deleted_context_archives CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS contexts CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS context_deletion_operations CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS composite_skills CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS attachment_path_migrations CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS artifacts CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS apply_journal CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS achievement_file_outbox CASCADE"))
