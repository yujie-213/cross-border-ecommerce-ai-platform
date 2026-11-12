"""Initial foundation schema, frozen DDL by module owner. No runtime table imports.

MySQL DDL autocommits. This migration does not claim transactional DDL rollback.
Destructive downgrade requires separate authorization and is deliberately refused.
"""
from alembic import op
from commerce_hub.infrastructure.database import MigrationError

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None

STATEMENTS = (
    'CREATE TABLE g01_principals (\n\ttenant_id VARCHAR(64) NOT NULL, \n\tprincipal_id VARCHAR(64) NOT NULL, \n\tactive BOOL NOT NULL, \n\trevision BIGINT NOT NULL, \n\tPRIMARY KEY (tenant_id, principal_id)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_bin',
    'CREATE TABLE g01_grants (\n\ttenant_id VARCHAR(64) NOT NULL, \n\tprincipal_id VARCHAR(64) NOT NULL, \n\taction VARCHAR(64) NOT NULL, \n\tscope JSON NOT NULL, \n\tPRIMARY KEY (tenant_id, principal_id, action), \n\tCONSTRAINT fk_g01_grant_principal FOREIGN KEY(tenant_id, principal_id) REFERENCES g01_principals (tenant_id, principal_id)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_bin',
    'CREATE TABLE g01_sessions (\n\ttenant_id VARCHAR(64) NOT NULL, \n\tprincipal_id VARCHAR(64) NOT NULL, \n\ttoken_id VARCHAR(64) NOT NULL, \n\tactive BOOL NOT NULL, \n\texpires_at DATETIME(6) NOT NULL, \n\tPRIMARY KEY (tenant_id, principal_id, token_id), \n\tCONSTRAINT fk_g01_session_principal FOREIGN KEY(tenant_id, principal_id) REFERENCES g01_principals (tenant_id, principal_id)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_bin',
    'CREATE TABLE g02_audit_events (\n\ttenant_id VARCHAR(64) NOT NULL, \n\tevent_id VARCHAR(64) NOT NULL, \n\ttask_id VARCHAR(64), \n\tprincipal_id VARCHAR(64) NOT NULL, \n\taction VARCHAR(64) NOT NULL, \n\tcode VARCHAR(64) NOT NULL, \n\toccurred_at DATETIME(6) NOT NULL, \n\ttrace_id VARCHAR(32) NOT NULL, \n\tdetails JSON NOT NULL, \n\tPRIMARY KEY (tenant_id, event_id)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_bin',
    'CREATE TABLE g02_usage_facts (\n\ttenant_id VARCHAR(64) NOT NULL, \n\ttask_id VARCHAR(64) NOT NULL, \n\tattempt_id VARCHAR(64) NOT NULL, \n\tusage_ref VARCHAR(64) NOT NULL, \n\ttokens INTEGER NOT NULL, \n\tcost NUMERIC(20, 8) NOT NULL, \n\tcurrency VARCHAR(8) NOT NULL, \n\tpricing_version VARCHAR(64) NOT NULL, \n\tPRIMARY KEY (tenant_id, task_id, attempt_id)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_bin',
    'CREATE TABLE o01_commands (\n\ttenant_id VARCHAR(64) NOT NULL, \n\tprincipal_id VARCHAR(64) NOT NULL, \n\tcommand_key VARCHAR(128) NOT NULL, \n\tfingerprint VARCHAR(64) NOT NULL, \n\ttask_id VARCHAR(64) NOT NULL, \n\trevision INTEGER NOT NULL, \n\tPRIMARY KEY (tenant_id, principal_id, command_key)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_bin',
    'CREATE TABLE o01_tasks (\n\ttenant_id VARCHAR(64) NOT NULL, \n\ttask_id VARCHAR(64) NOT NULL, \n\tprincipal_id VARCHAR(64) NOT NULL, \n\tcommand_key VARCHAR(128) NOT NULL, \n\tfingerprint VARCHAR(64) NOT NULL, \n\tscenario_id VARCHAR(64) NOT NULL, \n\tscenario_version VARCHAR(32) NOT NULL, \n\tplan_version INTEGER NOT NULL, \n\tscope JSON NOT NULL, \n\tparameters JSON NOT NULL, \n\tstate VARCHAR(24) NOT NULL, \n\trevision INTEGER NOT NULL, \n\twork_id VARCHAR(64) NOT NULL, \n\tcreated_at DATETIME(6) NOT NULL, \n\tdeadline DATETIME(6) NOT NULL, \n\terror_code VARCHAR(64), \n\tPRIMARY KEY (tenant_id, task_id), \n\tCONSTRAINT uq_o01_task_command UNIQUE (tenant_id, principal_id, command_key)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_bin',
    'CREATE TABLE o01_budgets (\n\ttenant_id VARCHAR(64) NOT NULL, \n\ttask_id VARCHAR(64) NOT NULL, \n\tpolicy_version VARCHAR(64) NOT NULL, \n\tmax_calls INTEGER NOT NULL, \n\tmax_tokens BIGINT NOT NULL, \n\tmax_cost NUMERIC(20, 8) NOT NULL, \n\tused_calls INTEGER NOT NULL, \n\tused_tokens BIGINT NOT NULL, \n\tused_cost NUMERIC(20, 8) NOT NULL, \n\treserved_calls INTEGER NOT NULL, \n\treserved_tokens BIGINT NOT NULL, \n\treserved_cost NUMERIC(20, 8) NOT NULL, \n\tPRIMARY KEY (tenant_id, task_id), \n\tCONSTRAINT fk_budget_task FOREIGN KEY(tenant_id, task_id) REFERENCES o01_tasks (tenant_id, task_id)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_bin',
    'CREATE TABLE o01_budget_attempts (\n\ttenant_id VARCHAR(64) NOT NULL, \n\ttask_id VARCHAR(64) NOT NULL, \n\tattempt_id VARCHAR(64) NOT NULL, \n\tlogical_call_id VARCHAR(64) NOT NULL, \n\tstate VARCHAR(24) NOT NULL, \n\tmax_tokens BIGINT NOT NULL, \n\tmax_cost NUMERIC(20, 8) NOT NULL, \n\tactual_tokens BIGINT, \n\tactual_cost NUMERIC(20, 8), \n\tusage_ref VARCHAR(64), \n\tPRIMARY KEY (tenant_id, task_id, attempt_id), \n\tCONSTRAINT fk_attempt_budget FOREIGN KEY(tenant_id, task_id) REFERENCES o01_budgets (tenant_id, task_id)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_bin',
    'CREATE TABLE i01_work_items (\n\ttenant_id VARCHAR(64) NOT NULL, \n\twork_id VARCHAR(64) NOT NULL, \n\towner_id VARCHAR(64) NOT NULL, \n\tkind VARCHAR(64) NOT NULL, \n\tstate VARCHAR(24) NOT NULL, \n\trun_after DATETIME(6) NOT NULL, \n\tattempt INTEGER NOT NULL, \n\tmax_attempts INTEGER NOT NULL, \n\tlease_token VARCHAR(64), \n\tlease_expires DATETIME(6), \n\tPRIMARY KEY (tenant_id, work_id)\n)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_bin',
    'CREATE INDEX ix_i01_claim ON i01_work_items (state, run_after, kind)',
    'CREATE INDEX ix_i01_expiry ON i01_work_items (state, lease_expires)',
 )


def upgrade():
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade():
    raise MigrationError("Destructive downgrade requires separate authorization; no tables were removed")
