"""initial

Revision ID: 0001
Revises: 
Create Date: 2026-10-01 12:04:47.497894
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Extensions (gen_random_uuid() is built in since PG13)
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin")
    op.create_table('compliance_policies',
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('severity', sa.String(length=8), server_default=sa.text("'MEDIUM'"), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_compliance_policies')),
    sa.UniqueConstraint('code', name=op.f('uq_compliance_policies_code'))
    )
    op.create_table('users',
    sa.Column('email', postgresql.CITEXT(), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('role', sa.String(length=16), nullable=False),
    sa.Column('full_name', sa.String(length=120), nullable=False),
    sa.Column('phone', sa.String(length=16), nullable=True),
    sa.Column('avatar_url', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deactivated_reason', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("email ~ '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$'", name=op.f('ck_users_email')),
    sa.CheckConstraint("phone IS NULL OR phone ~ '^\\+?[1-9][0-9]{9,14}$'", name=op.f('ck_users_phone')),
    sa.CheckConstraint("role IN ('ADMIN','FACULTY','STUDENT','COMPANY')", name=op.f('ck_users_role')),
    sa.CheckConstraint('length(trim(full_name)) >= 2', name=op.f('ck_users_full_name')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    op.create_index('ix_users_full_name_trgm', 'users', ['full_name'], unique=False, postgresql_using='gin', postgresql_ops={'full_name': 'gin_trgm_ops'})
    op.create_index('ix_users_role', 'users', ['role'], unique=False)
    op.create_table('audit_logs',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('actor_id', sa.UUID(), nullable=True),
    sa.Column('action', sa.String(length=60), nullable=False),
    sa.Column('entity_type', sa.String(length=40), nullable=False),
    sa.Column('entity_id', sa.UUID(), nullable=True),
    sa.Column('before', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('after', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('ip', postgresql.INET(), nullable=True),
    sa.Column('user_agent', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], name=op.f('fk_audit_logs_actor_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs'))
    )
    op.create_index('ix_audit_logs_actor_id', 'audit_logs', ['actor_id'], unique=False)
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)
    op.create_index('ix_audit_logs_entity_type_entity_id', 'audit_logs', ['entity_type', 'entity_id'], unique=False)
    op.create_table('documents',
    sa.Column('owner_id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('bucket', sa.String(length=32), nullable=False),
    sa.Column('object_key', sa.Text(), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('content_type', sa.String(length=100), nullable=False),
    sa.Column('size_bytes', sa.BigInteger(), nullable=False),
    sa.Column('status', sa.String(length=16), server_default=sa.text("'PENDING_UPLOAD'"), nullable=False),
    sa.Column('verification_status', sa.String(length=16), server_default=sa.text("'PENDING'"), nullable=False),
    sa.Column('verified_by', sa.UUID(), nullable=True),
    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('verification_note', sa.Text(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("bucket IN ('resumes','documents','reports')", name=op.f('ck_documents_bucket')),
    sa.CheckConstraint("kind <> 'RESUME' OR (content_type = 'application/pdf' AND size_bytes <= 5242880)", name=op.f('ck_documents_resume_pdf')),
    sa.CheckConstraint("kind IN ('RESUME','COVER_LETTER','TRANSCRIPT','OFFER_LETTER','LOGO','REPORT','EXPORT','IMPORT','OTHER')", name=op.f('ck_documents_kind')),
    sa.CheckConstraint("status IN ('PENDING_UPLOAD','UPLOADED','REJECTED')", name=op.f('ck_documents_status')),
    sa.CheckConstraint("verification_status IN ('PENDING','VERIFIED','REJECTED')", name=op.f('ck_documents_verification_status')),
    sa.CheckConstraint('size_bytes > 0', name=op.f('ck_documents_size_bytes')),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_documents_owner_id_users')),
    sa.ForeignKeyConstraint(['verified_by'], ['users.id'], name=op.f('fk_documents_verified_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_documents')),
    sa.UniqueConstraint('object_key', name=op.f('uq_documents_object_key'))
    )
    op.create_index('ix_documents_owner_id_kind', 'documents', ['owner_id', 'kind'], unique=False)
    op.create_table('evaluation_forms',
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('is_default', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_evaluation_forms_created_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_evaluation_forms'))
    )
    op.create_table('faculty',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('employee_id', sa.String(length=32), nullable=True),
    sa.Column('department', sa.String(length=80), nullable=False),
    sa.Column('designation', sa.String(length=80), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_faculty_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_faculty')),
    sa.UniqueConstraint('employee_id', name=op.f('uq_faculty_employee_id'))
    )
    op.create_table('login_events',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('email', postgresql.CITEXT(), nullable=True),
    sa.Column('success', sa.Boolean(), nullable=False),
    sa.Column('ip', postgresql.INET(), nullable=True),
    sa.Column('user_agent', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_login_events_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_login_events'))
    )
    op.create_index('ix_login_events_created_at', 'login_events', ['created_at'], unique=False)
    op.create_table('notifications',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('type', sa.String(length=40), nullable=False),
    sa.Column('title', sa.String(length=160), nullable=False),
    sa.Column('body', sa.Text(), server_default=sa.text("''"), nullable=False),
    sa.Column('link', sa.Text(), nullable=True),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notifications_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications'))
    )
    op.create_index('ix_notifications_user_id_read_at_created_at', 'notifications', ['user_id', 'read_at', sa.literal_column('created_at DESC')], unique=False)
    op.create_table('policy_violations',
    sa.Column('policy_id', sa.UUID(), nullable=False),
    sa.Column('entity_type', sa.String(length=40), nullable=False),
    sa.Column('entity_id', sa.UUID(), nullable=False),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('status', sa.String(length=10), server_default=sa.text("'OPEN'"), nullable=False),
    sa.Column('resolved_by', sa.UUID(), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('OPEN','RESOLVED','DISMISSED')", name=op.f('ck_policy_violations_status')),
    sa.ForeignKeyConstraint(['policy_id'], ['compliance_policies.id'], name=op.f('fk_policy_violations_policy_id_compliance_policies')),
    sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], name=op.f('fk_policy_violations_resolved_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_policy_violations')),
    sa.UniqueConstraint('policy_id', 'entity_type', 'entity_id', name='uq_policy_violations_policy_entity')
    )
    op.create_index('ix_policy_violations_status', 'policy_violations', ['status'], unique=False)
    op.create_table('refresh_tokens',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('family_id', sa.UUID(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('replaced_by_id', sa.UUID(), nullable=True),
    sa.Column('user_agent', sa.Text(), nullable=True),
    sa.Column('ip', postgresql.INET(), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_refresh_tokens_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_tokens')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_refresh_tokens_token_hash'))
    )
    op.create_index('ix_refresh_tokens_family_id', 'refresh_tokens', ['family_id'], unique=False)
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'], unique=False)
    op.create_table('system_feedback',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('type', sa.String(length=12), nullable=False),
    sa.Column('title', sa.String(length=160), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('page_url', sa.Text(), nullable=True),
    sa.Column('severity', sa.String(length=8), nullable=True),
    sa.Column('status', sa.String(length=12), server_default=sa.text("'NEW'"), nullable=False),
    sa.Column('priority', sa.String(length=8), nullable=True),
    sa.Column('admin_notes', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("priority IS NULL OR priority IN ('LOW','MEDIUM','HIGH')", name=op.f('ck_system_feedback_priority')),
    sa.CheckConstraint("severity IS NULL OR severity IN ('LOW','MEDIUM','HIGH','CRITICAL')", name=op.f('ck_system_feedback_severity')),
    sa.CheckConstraint("status IN ('NEW','TRIAGED','PLANNED','IN_PROGRESS','DONE','WONT_DO')", name=op.f('ck_system_feedback_status')),
    sa.CheckConstraint("type IN ('FEATURE','BUG','IMPROVEMENT')", name=op.f('ck_system_feedback_type')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_system_feedback_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_system_feedback'))
    )
    op.create_index('ix_system_feedback_status', 'system_feedback', ['status'], unique=False)
    op.create_index('ix_system_feedback_user_id', 'system_feedback', ['user_id'], unique=False)
    op.create_table('user_tokens',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('purpose', sa.String(length=16), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("purpose IN ('VERIFY_EMAIL','RESET_PASSWORD')", name=op.f('ck_user_tokens_purpose')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_tokens_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_user_tokens')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_user_tokens_token_hash'))
    )
    op.create_index('ix_user_tokens_user_id', 'user_tokens', ['user_id'], unique=False)
    op.create_table('companies',
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('registration_number', sa.String(length=32), nullable=False),
    sa.Column('industry', sa.String(length=80), nullable=True),
    sa.Column('location', sa.String(length=160), nullable=False),
    sa.Column('website', sa.Text(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('logo_document_id', sa.UUID(), nullable=True),
    sa.Column('contact_person_name', sa.String(length=120), nullable=False),
    sa.Column('contact_email', postgresql.CITEXT(), nullable=False),
    sa.Column('contact_phone', sa.String(length=16), nullable=True),
    sa.Column('status', sa.String(length=16), server_default=sa.text("'ACTIVE'"), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("contact_phone IS NULL OR contact_phone ~ '^\\+?[1-9][0-9]{9,14}$'", name=op.f('ck_companies_contact_phone')),
    sa.CheckConstraint("registration_number ~ '^([LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}|[A-Z]{2}-[A-Z0-9]{6,15})$'", name=op.f('ck_companies_registration_number')),
    sa.CheckConstraint("status IN ('PENDING','ACTIVE','ARCHIVED')", name=op.f('ck_companies_status')),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_companies_created_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['logo_document_id'], ['documents.id'], name=op.f('fk_companies_logo_document_id_documents'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_companies')),
    sa.UniqueConstraint('registration_number', name=op.f('uq_companies_registration_number'))
    )
    op.create_index('ix_companies_name_trgm', 'companies', ['name'], unique=False, postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.create_index('ix_companies_status', 'companies', ['status'], unique=False)
    op.create_table('evaluation_criteria',
    sa.Column('form_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('weight', sa.Numeric(precision=4, scale=2), server_default=sa.text('1'), nullable=False),
    sa.Column('max_score', sa.SmallInteger(), server_default=sa.text('5'), nullable=False),
    sa.Column('position', sa.SmallInteger(), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('max_score IN (5,10)', name=op.f('ck_evaluation_criteria_max_score')),
    sa.CheckConstraint('weight > 0 AND weight <= 10', name=op.f('ck_evaluation_criteria_weight')),
    sa.ForeignKeyConstraint(['form_id'], ['evaluation_forms.id'], name=op.f('fk_evaluation_criteria_form_id_evaluation_forms'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_evaluation_criteria')),
    sa.UniqueConstraint('form_id', 'position', name='uq_evaluation_criteria_form_position')
    )
    op.create_index('ix_evaluation_criteria_form_id', 'evaluation_criteria', ['form_id'], unique=False)
    op.create_table('feedback_action_items',
    sa.Column('system_feedback_id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=160), nullable=False),
    sa.Column('assignee_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.String(length=12), server_default=sa.text("'OPEN'"), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('OPEN','IN_PROGRESS','DONE')", name=op.f('ck_feedback_action_items_status')),
    sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], name=op.f('fk_feedback_action_items_assignee_id_users')),
    sa.ForeignKeyConstraint(['system_feedback_id'], ['system_feedback.id'], name=op.f('fk_feedback_action_items_system_feedback_id_system_feedback'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_feedback_action_items'))
    )
    op.create_index('ix_feedback_action_items_system_feedback_id', 'feedback_action_items', ['system_feedback_id'], unique=False)
    op.create_table('jobs',
    sa.Column('type', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=12), server_default=sa.text("'QUEUED'"), nullable=False),
    sa.Column('requested_by', sa.UUID(), nullable=True),
    sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('progress', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('result_document_id', sa.UUID(), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED')", name=op.f('ck_jobs_status')),
    sa.CheckConstraint("type IN ('REPORT_EXPORT','DATA_EXPORT','DATA_IMPORT','COMPLIANCE_SCAN')", name=op.f('ck_jobs_type')),
    sa.CheckConstraint('progress BETWEEN 0 AND 100', name=op.f('ck_jobs_progress')),
    sa.ForeignKeyConstraint(['requested_by'], ['users.id'], name=op.f('fk_jobs_requested_by_users')),
    sa.ForeignKeyConstraint(['result_document_id'], ['documents.id'], name=op.f('fk_jobs_result_document_id_documents')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_jobs'))
    )
    op.create_index('ix_jobs_requested_by', 'jobs', ['requested_by'], unique=False)
    op.create_index('ix_jobs_type_status', 'jobs', ['type', 'status'], unique=False)
    op.create_table('students',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('enrollment_no', sa.String(length=32), nullable=True),
    sa.Column('department', sa.String(length=80), nullable=False),
    sa.Column('gpa', sa.Numeric(precision=3, scale=2), nullable=False),
    sa.Column('graduation_year', sa.SmallInteger(), nullable=True),
    sa.Column('skills', postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
    sa.Column('bio', sa.Text(), nullable=True),
    sa.Column('linkedin_url', sa.Text(), nullable=True),
    sa.Column('github_url', sa.Text(), nullable=True),
    sa.Column('portfolio_url', sa.Text(), nullable=True),
    sa.Column('default_resume_id', sa.UUID(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('bio IS NULL OR length(bio) <= 2000', name=op.f('ck_students_bio')),
    sa.CheckConstraint('gpa >= 0.0 AND gpa <= 4.0', name=op.f('ck_students_gpa')),
    sa.CheckConstraint('graduation_year IS NULL OR graduation_year BETWEEN 2000 AND 2100', name=op.f('ck_students_graduation_year')),
    sa.ForeignKeyConstraint(['default_resume_id'], ['documents.id'], name=op.f('fk_students_default_resume_id_documents'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_students_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_students')),
    sa.UniqueConstraint('enrollment_no', name=op.f('uq_students_enrollment_no'))
    )
    op.create_index('ix_students_department', 'students', ['department'], unique=False)
    op.create_index('ix_students_gpa', 'students', ['gpa'], unique=False)
    op.create_table('company_members',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('job_title', sa.String(length=80), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('fk_company_members_company_id_companies'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_company_members_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_company_members'))
    )
    op.create_index('ix_company_members_company_id', 'company_members', ['company_id'], unique=False)
    op.create_table('internships',
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('posted_by', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=160), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('domain', sa.String(length=60), nullable=False),
    sa.Column('location', sa.String(length=160), nullable=False),
    sa.Column('work_mode', sa.String(length=10), nullable=False),
    sa.Column('stipend_monthly', sa.Numeric(precision=10, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('currency', sa.String(length=3), server_default=sa.text("'INR'"), nullable=False),
    sa.Column('duration_weeks', sa.SmallInteger(), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=False),
    sa.Column('application_deadline', sa.DateTime(timezone=True), nullable=False),
    sa.Column('openings', sa.SmallInteger(), server_default=sa.text('1'), nullable=False),
    sa.Column('skills', postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
    sa.Column('min_gpa', sa.Numeric(precision=3, scale=2), nullable=True),
    sa.Column('eligible_departments', postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'DRAFT'"), nullable=False),
    sa.Column('rejection_reason', sa.Text(), nullable=True),
    sa.Column('approved_by', sa.UUID(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('search_vector', postgresql.TSVECTOR(), sa.Computed("setweight(to_tsvector('english'::regconfig, coalesce(title,'')), 'A') || setweight(to_tsvector('english'::regconfig, coalesce(domain,'')), 'B') || setweight(to_tsvector('english'::regconfig, coalesce(location,'')), 'C') || setweight(to_tsvector('english'::regconfig, coalesce(description,'')), 'D')", persisted=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("status IN ('DRAFT','PENDING_APPROVAL','APPROVED','REJECTED','CLOSED')", name=op.f('ck_internships_status')),
    sa.CheckConstraint("work_mode IN ('ONSITE','REMOTE','HYBRID')", name=op.f('ck_internships_work_mode')),
    sa.CheckConstraint('(end_date - start_date) BETWEEN 28 AND 183', name=op.f('ck_internships_duration_days')),
    sa.CheckConstraint('application_deadline < start_date::timestamptz', name=op.f('ck_internships_deadline_before_start')),
    sa.CheckConstraint('duration_weeks BETWEEN 4 AND 26', name=op.f('ck_internships_duration_weeks')),
    sa.CheckConstraint('length(description) >= 20', name=op.f('ck_internships_description')),
    sa.CheckConstraint('length(title) >= 3', name=op.f('ck_internships_title')),
    sa.CheckConstraint('min_gpa IS NULL OR (min_gpa >= 0 AND min_gpa <= 4)', name=op.f('ck_internships_min_gpa')),
    sa.CheckConstraint('openings > 0', name=op.f('ck_internships_openings')),
    sa.CheckConstraint('start_date < end_date', name=op.f('ck_internships_dates')),
    sa.CheckConstraint('stipend_monthly >= 0', name=op.f('ck_internships_stipend')),
    sa.ForeignKeyConstraint(['approved_by'], ['users.id'], name=op.f('fk_internships_approved_by_users')),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('fk_internships_company_id_companies'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['posted_by'], ['users.id'], name=op.f('fk_internships_posted_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_internships'))
    )
    op.create_index('ix_internships_company_id', 'internships', ['company_id'], unique=False)
    op.create_index('ix_internships_domain', 'internships', ['domain'], unique=False)
    op.create_index('ix_internships_open', 'internships', ['application_deadline'], unique=False, postgresql_where=sa.text("status = 'APPROVED' AND archived_at IS NULL"))
    op.create_index('ix_internships_posted_by', 'internships', ['posted_by'], unique=False)
    op.create_index('ix_internships_search_vector', 'internships', ['search_vector'], unique=False, postgresql_using='gin')
    op.create_index('ix_internships_status_application_deadline', 'internships', ['status', 'application_deadline'], unique=False)
    op.create_index('ix_internships_stipend_monthly', 'internships', ['stipend_monthly'], unique=False)
    op.create_index('ix_internships_title_trgm', 'internships', ['title'], unique=False, postgresql_using='gin', postgresql_ops={'title': 'gin_trgm_ops'})
    op.create_table('applications',
    sa.Column('internship_id', sa.UUID(), nullable=False),
    sa.Column('student_id', sa.UUID(), nullable=False),
    sa.Column('resume_document_id', sa.UUID(), nullable=False),
    sa.Column('cover_letter', sa.Text(), nullable=False),
    sa.Column('qualifications', sa.Text(), nullable=False),
    sa.Column('answers', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('status', sa.String(length=16), server_default=sa.text("'PENDING'"), nullable=False),
    sa.Column('status_changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('decision_note', sa.Text(), nullable=True),
    sa.Column('offer_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('withdrawn_reason', sa.Text(), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('PENDING','UNDER_REVIEW','SHORTLISTED','INTERVIEW','ACCEPTED','REJECTED','WITHDRAWN')", name=op.f('ck_applications_status')),
    sa.CheckConstraint('length(cover_letter) BETWEEN 50 AND 5000', name=op.f('ck_applications_cover_letter')),
    sa.CheckConstraint('length(qualifications) BETWEEN 10 AND 3000', name=op.f('ck_applications_qualifications')),
    sa.ForeignKeyConstraint(['internship_id'], ['internships.id'], name=op.f('fk_applications_internship_id_internships'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['resume_document_id'], ['documents.id'], name=op.f('fk_applications_resume_document_id_documents')),
    sa.ForeignKeyConstraint(['student_id'], ['students.user_id'], name=op.f('fk_applications_student_id_students')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_applications')),
    sa.UniqueConstraint('student_id', 'internship_id', name='uq_applications_student_internship')
    )
    op.create_index('ix_applications_internship_id_status', 'applications', ['internship_id', 'status'], unique=False)
    op.create_index('ix_applications_status_changed_at', 'applications', ['status_changed_at'], unique=False)
    op.create_index('ix_applications_student_id_status', 'applications', ['student_id', 'status'], unique=False)
    op.create_table('saved_internships',
    sa.Column('student_id', sa.UUID(), nullable=False),
    sa.Column('internship_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['internship_id'], ['internships.id'], name=op.f('fk_saved_internships_internship_id_internships'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['student_id'], ['students.user_id'], name=op.f('fk_saved_internships_student_id_students'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('student_id', 'internship_id', name=op.f('pk_saved_internships'))
    )
    op.create_table('application_status_history',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('application_id', sa.UUID(), nullable=False),
    sa.Column('from_status', sa.String(length=16), nullable=True),
    sa.Column('to_status', sa.String(length=16), nullable=False),
    sa.Column('changed_by', sa.UUID(), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], name=op.f('fk_application_status_history_application_id_applications'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['changed_by'], ['users.id'], name=op.f('fk_application_status_history_changed_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_application_status_history'))
    )
    op.create_index('ix_application_status_history_application_id_created_at', 'application_status_history', ['application_id', 'created_at'], unique=False)
    op.create_table('company_feedback',
    sa.Column('application_id', sa.UUID(), nullable=False),
    sa.Column('author_id', sa.UUID(), nullable=False),
    sa.Column('technical_skills', sa.SmallInteger(), nullable=False),
    sa.Column('soft_skills', sa.SmallInteger(), nullable=False),
    sa.Column('punctuality', sa.SmallInteger(), nullable=False),
    sa.Column('responsibility', sa.SmallInteger(), nullable=False),
    sa.Column('teamwork', sa.SmallInteger(), nullable=False),
    sa.Column('learning_ability', sa.SmallInteger(), nullable=False),
    sa.Column('strengths', sa.Text(), nullable=True),
    sa.Column('improvements', sa.Text(), nullable=True),
    sa.Column('hire_likelihood', sa.SmallInteger(), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('hire_likelihood BETWEEN 1 AND 5', name=op.f('ck_company_feedback_hire_likelihood')),
    sa.CheckConstraint('learning_ability BETWEEN 1 AND 5', name=op.f('ck_company_feedback_learning_ability')),
    sa.CheckConstraint('punctuality BETWEEN 1 AND 5', name=op.f('ck_company_feedback_punctuality')),
    sa.CheckConstraint('responsibility BETWEEN 1 AND 5', name=op.f('ck_company_feedback_responsibility')),
    sa.CheckConstraint('soft_skills BETWEEN 1 AND 5', name=op.f('ck_company_feedback_soft_skills')),
    sa.CheckConstraint('teamwork BETWEEN 1 AND 5', name=op.f('ck_company_feedback_teamwork')),
    sa.CheckConstraint('technical_skills BETWEEN 1 AND 5', name=op.f('ck_company_feedback_technical_skills')),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], name=op.f('fk_company_feedback_application_id_applications')),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], name=op.f('fk_company_feedback_author_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_company_feedback')),
    sa.UniqueConstraint('application_id', 'author_id', name='uq_company_feedback_application_author')
    )
    op.create_index('ix_company_feedback_application_id', 'company_feedback', ['application_id'], unique=False)
    op.create_table('evaluations',
    sa.Column('form_id', sa.UUID(), nullable=False),
    sa.Column('application_id', sa.UUID(), nullable=False),
    sa.Column('evaluator_id', sa.UUID(), nullable=False),
    sa.Column('overall_comments', sa.Text(), nullable=True),
    sa.Column('recommendation', sa.String(length=16), nullable=False),
    sa.Column('weighted_score', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('shared_with_student', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("recommendation IN ('STRONG_YES','YES','MAYBE','NO')", name=op.f('ck_evaluations_recommendation')),
    sa.CheckConstraint('weighted_score >= 0 AND weighted_score <= 100', name=op.f('ck_evaluations_weighted_score')),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], name=op.f('fk_evaluations_application_id_applications'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['evaluator_id'], ['users.id'], name=op.f('fk_evaluations_evaluator_id_users')),
    sa.ForeignKeyConstraint(['form_id'], ['evaluation_forms.id'], name=op.f('fk_evaluations_form_id_evaluation_forms')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_evaluations')),
    sa.UniqueConstraint('application_id', 'evaluator_id', 'form_id', name='uq_evaluations_application_evaluator_form')
    )
    op.create_index('ix_evaluations_application_id', 'evaluations', ['application_id'], unique=False)
    op.create_index('ix_evaluations_evaluator_id', 'evaluations', ['evaluator_id'], unique=False)
    op.create_table('faculty_feedback',
    sa.Column('internship_id', sa.UUID(), nullable=False),
    sa.Column('application_id', sa.UUID(), nullable=True),
    sa.Column('faculty_id', sa.UUID(), nullable=False),
    sa.Column('course_suitability', sa.SmallInteger(), nullable=False),
    sa.Column('learning_outcomes', sa.SmallInteger(), nullable=False),
    sa.Column('internship_quality', sa.SmallInteger(), nullable=False),
    sa.Column('suggestions', sa.Text(), nullable=True),
    sa.Column('comments', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('course_suitability BETWEEN 1 AND 5', name=op.f('ck_faculty_feedback_course_suitability')),
    sa.CheckConstraint('internship_quality BETWEEN 1 AND 5', name=op.f('ck_faculty_feedback_internship_quality')),
    sa.CheckConstraint('learning_outcomes BETWEEN 1 AND 5', name=op.f('ck_faculty_feedback_learning_outcomes')),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], name=op.f('fk_faculty_feedback_application_id_applications')),
    sa.ForeignKeyConstraint(['faculty_id'], ['users.id'], name=op.f('fk_faculty_feedback_faculty_id_users')),
    sa.ForeignKeyConstraint(['internship_id'], ['internships.id'], name=op.f('fk_faculty_feedback_internship_id_internships')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_faculty_feedback'))
    )
    op.create_index('ix_faculty_feedback_internship_id', 'faculty_feedback', ['internship_id'], unique=False)
    op.create_table('interviews',
    sa.Column('application_id', sa.UUID(), nullable=False),
    sa.Column('scheduled_by', sa.UUID(), nullable=False),
    sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('duration_minutes', sa.SmallInteger(), server_default=sa.text('30'), nullable=False),
    sa.Column('mode', sa.String(length=10), nullable=False),
    sa.Column('location', sa.Text(), nullable=True),
    sa.Column('meeting_link', sa.Text(), nullable=True),
    sa.Column('interviewer_name', sa.String(length=120), nullable=False),
    sa.Column('interviewer_email', postgresql.CITEXT(), nullable=True),
    sa.Column('interviewer_user_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.String(length=12), server_default=sa.text("'SCHEDULED'"), nullable=False),
    sa.Column('result', sa.String(length=10), server_default=sa.text("'PENDING'"), nullable=False),
    sa.Column('score', sa.SmallInteger(), nullable=True),
    sa.Column('comments', sa.Text(), nullable=True),
    sa.Column('feedback_for_student', sa.Text(), nullable=True),
    sa.Column('cancel_reason', sa.Text(), nullable=True),
    sa.Column('reschedule_count', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("mode IN ('ONLINE','ONSITE','PHONE')", name=op.f('ck_interviews_mode')),
    sa.CheckConstraint("result IN ('PENDING','PASS','FAIL','ON_HOLD')", name=op.f('ck_interviews_result')),
    sa.CheckConstraint("status IN ('SCHEDULED','RESCHEDULED','COMPLETED','CANCELLED','NO_SHOW')", name=op.f('ck_interviews_status')),
    sa.CheckConstraint('duration_minutes BETWEEN 15 AND 240', name=op.f('ck_interviews_duration_minutes')),
    sa.CheckConstraint('score IS NULL OR score BETWEEN 1 AND 5', name=op.f('ck_interviews_score')),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], name=op.f('fk_interviews_application_id_applications'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['interviewer_user_id'], ['users.id'], name=op.f('fk_interviews_interviewer_user_id_users')),
    sa.ForeignKeyConstraint(['scheduled_by'], ['users.id'], name=op.f('fk_interviews_scheduled_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_interviews'))
    )
    op.create_index('ix_interviews_application_id', 'interviews', ['application_id'], unique=False)
    op.create_index('ix_interviews_interviewer_user_id_scheduled_at', 'interviews', ['interviewer_user_id', 'scheduled_at'], unique=False)
    op.create_index('ix_interviews_scheduled_at', 'interviews', ['scheduled_at'], unique=False)
    op.create_table('student_feedback',
    sa.Column('application_id', sa.UUID(), nullable=False),
    sa.Column('student_id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('internship_id', sa.UUID(), nullable=False),
    sa.Column('company_culture', sa.SmallInteger(), nullable=False),
    sa.Column('mentorship', sa.SmallInteger(), nullable=False),
    sa.Column('technical_learning', sa.SmallInteger(), nullable=False),
    sa.Column('work_environment', sa.SmallInteger(), nullable=False),
    sa.Column('overall', sa.SmallInteger(), nullable=False),
    sa.Column('comments', sa.Text(), nullable=True),
    sa.Column('suggestions', sa.Text(), nullable=True),
    sa.Column('is_anonymous', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('response_body', sa.Text(), nullable=True),
    sa.Column('responded_by', sa.UUID(), nullable=True),
    sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('company_culture BETWEEN 1 AND 5', name=op.f('ck_student_feedback_company_culture')),
    sa.CheckConstraint('mentorship BETWEEN 1 AND 5', name=op.f('ck_student_feedback_mentorship')),
    sa.CheckConstraint('overall BETWEEN 1 AND 5', name=op.f('ck_student_feedback_overall')),
    sa.CheckConstraint('technical_learning BETWEEN 1 AND 5', name=op.f('ck_student_feedback_technical_learning')),
    sa.CheckConstraint('work_environment BETWEEN 1 AND 5', name=op.f('ck_student_feedback_work_environment')),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], name=op.f('fk_student_feedback_application_id_applications')),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('fk_student_feedback_company_id_companies')),
    sa.ForeignKeyConstraint(['internship_id'], ['internships.id'], name=op.f('fk_student_feedback_internship_id_internships')),
    sa.ForeignKeyConstraint(['responded_by'], ['users.id'], name=op.f('fk_student_feedback_responded_by_users')),
    sa.ForeignKeyConstraint(['student_id'], ['students.user_id'], name=op.f('fk_student_feedback_student_id_students')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_student_feedback')),
    sa.UniqueConstraint('application_id', name=op.f('uq_student_feedback_application_id'))
    )
    op.create_index('ix_student_feedback_company_id_created_at', 'student_feedback', ['company_id', 'created_at'], unique=False)
    op.create_index('ix_student_feedback_internship_id', 'student_feedback', ['internship_id'], unique=False)
    op.create_table('evaluation_scores',
    sa.Column('evaluation_id', sa.UUID(), nullable=False),
    sa.Column('criterion_id', sa.UUID(), nullable=False),
    sa.Column('score', sa.SmallInteger(), nullable=False),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.CheckConstraint('score BETWEEN 0 AND 10', name=op.f('ck_evaluation_scores_score')),
    sa.ForeignKeyConstraint(['criterion_id'], ['evaluation_criteria.id'], name=op.f('fk_evaluation_scores_criterion_id_evaluation_criteria')),
    sa.ForeignKeyConstraint(['evaluation_id'], ['evaluations.id'], name=op.f('fk_evaluation_scores_evaluation_id_evaluations'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('evaluation_id', 'criterion_id', name=op.f('pk_evaluation_scores'))
    )


    # ------------------------------------------------------------------ seed data
    # Default evaluation form "Standard Internship Evaluation" with 5 criteria (max_score 5)
    op.execute(
        """
        INSERT INTO evaluation_forms (id, name, description, is_default)
        VALUES ('00000000-0000-0000-0000-00000000e001', 'Standard Internship Evaluation',
                'Default rubric used for internship candidate evaluation.', true)
        """
    )
    criteria = [
        ("Technical Skills", "Depth and accuracy of technical knowledge relevant to the role."),
        ("Problem Solving", "Ability to analyse problems and design sound solutions."),
        ("Communication", "Clarity of written and verbal communication."),
        ("Culture Fit", "Alignment with team values and collaboration style."),
        ("Initiative", "Proactiveness, curiosity and ownership."),
    ]
    for position, (name, description) in enumerate(criteria, start=1):
        op.execute(
            sa.text(
                "INSERT INTO evaluation_criteria (form_id, name, description, weight, max_score, position) "
                "VALUES ('00000000-0000-0000-0000-00000000e001', :name, :description, 1, 5, :position)"
            ).bindparams(name=name, description=description, position=position)
        )

    # Compliance policies (plan 3.12)
    policies = [
        ("RESUME_UNVERIFIED_7D", "Resume pending verification for more than 7 days",
         "A resume attached to an active application has been PENDING verification for more than 7 days.", "MEDIUM"),
        ("INTERNSHIP_PAST_DEADLINE_OPEN", "Approved internship past deadline but not closed",
         "An approved internship's application deadline passed but it was not closed.", "LOW"),
        ("INTERVIEW_SHORT_NOTICE", "Interview scheduled with less than 24h notice",
         "Should never fire; detects data that bypassed the 24h notice rule.", "HIGH"),
        ("UNPAID_LONG_INTERNSHIP", "Unpaid internship longer than 12 weeks",
         "Stipend is 0 and duration is greater than 12 weeks.", "MEDIUM"),
        ("INACTIVE_COMPANY_POSTING", "Internship belongs to an archived or pending company",
         "An internship belongs to a company that is ARCHIVED or PENDING.", "HIGH"),
    ]
    for code, name, description, severity in policies:
        op.execute(
            sa.text(
                "INSERT INTO compliance_policies (code, name, description, is_active, severity) "
                "VALUES (:code, :name, :description, true, :severity)"
            ).bindparams(code=code, name=name, description=description, severity=severity)
        )


def downgrade() -> None:
    op.drop_table('evaluation_scores')
    op.drop_index('ix_student_feedback_internship_id', table_name='student_feedback')
    op.drop_index('ix_student_feedback_company_id_created_at', table_name='student_feedback')
    op.drop_table('student_feedback')
    op.drop_index('ix_interviews_scheduled_at', table_name='interviews')
    op.drop_index('ix_interviews_interviewer_user_id_scheduled_at', table_name='interviews')
    op.drop_index('ix_interviews_application_id', table_name='interviews')
    op.drop_table('interviews')
    op.drop_index('ix_faculty_feedback_internship_id', table_name='faculty_feedback')
    op.drop_table('faculty_feedback')
    op.drop_index('ix_evaluations_evaluator_id', table_name='evaluations')
    op.drop_index('ix_evaluations_application_id', table_name='evaluations')
    op.drop_table('evaluations')
    op.drop_index('ix_company_feedback_application_id', table_name='company_feedback')
    op.drop_table('company_feedback')
    op.drop_index('ix_application_status_history_application_id_created_at', table_name='application_status_history')
    op.drop_table('application_status_history')
    op.drop_table('saved_internships')
    op.drop_index('ix_applications_student_id_status', table_name='applications')
    op.drop_index('ix_applications_status_changed_at', table_name='applications')
    op.drop_index('ix_applications_internship_id_status', table_name='applications')
    op.drop_table('applications')
    op.drop_index('ix_internships_title_trgm', table_name='internships', postgresql_using='gin', postgresql_ops={'title': 'gin_trgm_ops'})
    op.drop_index('ix_internships_stipend_monthly', table_name='internships')
    op.drop_index('ix_internships_status_application_deadline', table_name='internships')
    op.drop_index('ix_internships_search_vector', table_name='internships', postgresql_using='gin')
    op.drop_index('ix_internships_posted_by', table_name='internships')
    op.drop_index('ix_internships_open', table_name='internships', postgresql_where=sa.text("status = 'APPROVED' AND archived_at IS NULL"))
    op.drop_index('ix_internships_domain', table_name='internships')
    op.drop_index('ix_internships_company_id', table_name='internships')
    op.drop_table('internships')
    op.drop_index('ix_company_members_company_id', table_name='company_members')
    op.drop_table('company_members')
    op.drop_index('ix_students_gpa', table_name='students')
    op.drop_index('ix_students_department', table_name='students')
    op.drop_table('students')
    op.drop_index('ix_jobs_type_status', table_name='jobs')
    op.drop_index('ix_jobs_requested_by', table_name='jobs')
    op.drop_table('jobs')
    op.drop_index('ix_feedback_action_items_system_feedback_id', table_name='feedback_action_items')
    op.drop_table('feedback_action_items')
    op.drop_index('ix_evaluation_criteria_form_id', table_name='evaluation_criteria')
    op.drop_table('evaluation_criteria')
    op.drop_index('ix_companies_status', table_name='companies')
    op.drop_index('ix_companies_name_trgm', table_name='companies', postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.drop_table('companies')
    op.drop_index('ix_user_tokens_user_id', table_name='user_tokens')
    op.drop_table('user_tokens')
    op.drop_index('ix_system_feedback_user_id', table_name='system_feedback')
    op.drop_index('ix_system_feedback_status', table_name='system_feedback')
    op.drop_table('system_feedback')
    op.drop_index('ix_refresh_tokens_user_id', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_family_id', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_index('ix_policy_violations_status', table_name='policy_violations')
    op.drop_table('policy_violations')
    op.drop_index('ix_notifications_user_id_read_at_created_at', table_name='notifications')
    op.drop_table('notifications')
    op.drop_index('ix_login_events_created_at', table_name='login_events')
    op.drop_table('login_events')
    op.drop_table('faculty')
    op.drop_table('evaluation_forms')
    op.drop_index('ix_documents_owner_id_kind', table_name='documents')
    op.drop_table('documents')
    op.drop_index('ix_audit_logs_entity_type_entity_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_actor_id', table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index('ix_users_role', table_name='users')
    op.drop_index('ix_users_full_name_trgm', table_name='users', postgresql_using='gin', postgresql_ops={'full_name': 'gin_trgm_ops'})
    op.drop_table('users')
    op.drop_table('compliance_policies')
