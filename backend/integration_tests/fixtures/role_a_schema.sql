
CREATE TABLE approvals (
	id VARCHAR(36) NOT NULL,
	content_id VARCHAR(36) NOT NULL,
	revision_id VARCHAR(36) NOT NULL,
	body_hash VARCHAR(64) NOT NULL,
	reviewer_id VARCHAR(36) NOT NULL,
	decision VARCHAR(30) NOT NULL,
	comment TEXT,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE TABLE audit_events (
	id VARCHAR(36) NOT NULL,
	org_id VARCHAR(36) NOT NULL,
	actor_id VARCHAR(36),
	event_type VARCHAR(60) NOT NULL,
	entity_type VARCHAR(60) NOT NULL,
	entity_id VARCHAR(36) NOT NULL,
	payload JSON NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE TABLE brands (
	id VARCHAR(36) NOT NULL,
	org_id VARCHAR(36) NOT NULL,
	name VARCHAR(120) NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE TABLE comments (
	id VARCHAR(36) NOT NULL,
	content_id VARCHAR(36) NOT NULL,
	revision_id VARCHAR(36) NOT NULL,
	finding_id VARCHAR(36),
	user_id VARCHAR(36) NOT NULL,
	body TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE TABLE content_items (
	id VARCHAR(36) NOT NULL,
	org_id VARCHAR(36) NOT NULL,
	brand_id VARCHAR(36) NOT NULL,
	title VARCHAR(255) NOT NULL,
	created_by VARCHAR(36) NOT NULL,
	status VARCHAR(30) NOT NULL,
	current_revision_id VARCHAR(36),
	latest_run_id VARCHAR(36),
	PRIMARY KEY (id)
)

;

CREATE TABLE content_revisions (
	id VARCHAR(36) NOT NULL,
	content_id VARCHAR(36) NOT NULL,
	number INTEGER NOT NULL,
	body_text TEXT NOT NULL,
	body_hash VARCHAR(64) NOT NULL,
	created_by VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	context JSON NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE TABLE documents (
	id VARCHAR(36) NOT NULL,
	org_id VARCHAR(36) NOT NULL,
	brand_id VARCHAR(36) NOT NULL,
	title VARCHAR(255) NOT NULL,
	kind VARCHAR(40) NOT NULL,
	filename VARCHAR(255) NOT NULL,
	file_bytes BYTEA NOT NULL,
	text TEXT NOT NULL,
	version INTEGER NOT NULL,
	content_hash VARCHAR(64) NOT NULL,
	uploaded_by VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE TABLE facts (
	id VARCHAR(36) NOT NULL,
	org_id VARCHAR(36) NOT NULL,
	brand_id VARCHAR(36) NOT NULL,
	product VARCHAR(120) NOT NULL,
	attribute VARCHAR(40) NOT NULL,
	value_text VARCHAR(255) NOT NULL,
	value_num FLOAT,
	unit VARCHAR(40),
	market VARCHAR(20) NOT NULL,
	valid_from DATE,
	valid_to DATE,
	status VARCHAR(20) NOT NULL,
	version INTEGER NOT NULL,
	source_document_id VARCHAR(36),
	source_location VARCHAR(100),
	PRIMARY KEY (id)
)

;

CREATE TABLE findings (
	id VARCHAR(36) NOT NULL,
	review_run_id VARCHAR(36) NOT NULL,
	revision_id VARCHAR(36) NOT NULL,
	origin VARCHAR(20) NOT NULL,
	category VARCHAR(30) NOT NULL,
	severity VARCHAR(20) NOT NULL,
	confidence FLOAT NOT NULL,
	verdict VARCHAR(30) NOT NULL,
	span_start INTEGER NOT NULL,
	span_end INTEGER NOT NULL,
	quoted_text TEXT NOT NULL,
	rule_id VARCHAR(36),
	fact_id VARCHAR(36),
	explanation TEXT NOT NULL,
	suggested_fix TEXT,
	status VARCHAR(20) NOT NULL,
	decision_note TEXT,
	edited_text TEXT,
	decided_by VARCHAR(36),
	PRIMARY KEY (id)
)

;

CREATE TABLE organisations (
	id VARCHAR(36) NOT NULL,
	name VARCHAR(120) NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE TABLE review_runs (
	id VARCHAR(36) NOT NULL,
	revision_id VARCHAR(36) NOT NULL,
	status VARCHAR(20) NOT NULL,
	progress_step VARCHAR(30) NOT NULL,
	applied_rules JSON NOT NULL,
	skipped JSON NOT NULL,
	ai_used BOOLEAN NOT NULL,
	error TEXT,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	finished_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id)
)

;

CREATE TABLE rules (
	id VARCHAR(36) NOT NULL,
	org_id VARCHAR(36) NOT NULL,
	brand_id VARCHAR(36) NOT NULL,
	code VARCHAR(40) NOT NULL,
	instruction TEXT NOT NULL,
	category VARCHAR(30) NOT NULL,
	severity VARCHAR(20) NOT NULL,
	scope_channel JSON NOT NULL,
	scope_audience JSON NOT NULL,
	scope_region JSON NOT NULL,
	scope_content_type JSON NOT NULL,
	scope_campaign JSON NOT NULL,
	authority VARCHAR(30) NOT NULL,
	overrideable BOOLEAN NOT NULL,
	priority INTEGER NOT NULL,
	forbidden_terms JSON NOT NULL,
	preferred_terms JSON NOT NULL,
	required_text TEXT,
	effective_from DATE,
	effective_to DATE,
	status VARCHAR(20) NOT NULL,
	version INTEGER NOT NULL,
	source_document_id VARCHAR(36),
	source_location VARCHAR(100),
	source_excerpt TEXT,
	confidence FLOAT NOT NULL,
	approved_by VARCHAR(36),
	PRIMARY KEY (id)
)

;

CREATE TABLE users (
	id VARCHAR(36) NOT NULL,
	org_id VARCHAR(36) NOT NULL,
	email VARCHAR(255) NOT NULL,
	name VARCHAR(120) NOT NULL,
	role VARCHAR(20) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(org_id) REFERENCES organisations (id)
)

;
