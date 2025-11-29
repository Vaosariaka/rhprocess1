-- base2.sql
-- Schema for HR system: employees, contracts, payroll, leaves, presence, documents, alerts, histories

CREATE DATABASE hrms;

\c hrms;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================================
-- Employees and related reference tables
-- =====================================================================
CREATE TABLE department (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE
);

CREATE TABLE gender (
    code VARCHAR(10) PRIMARY KEY,
    label VARCHAR(50) NOT NULL
);

CREATE TABLE employee (
    id SERIAL PRIMARY KEY,
    matricule VARCHAR(50) UNIQUE,
    first_name VARCHAR(150) NOT NULL,
    last_name VARCHAR(150) NOT NULL,
    gender_code VARCHAR(10) REFERENCES gender(code),
    date_birth DATE,
    address TEXT,
    phone VARCHAR(50),
    email VARCHAR(254),
    cnaps_number VARCHAR(100),
    hire_date DATE,
    termination_date DATE,
    salary_base NUMERIC(12,2) DEFAULT 0,
    job_title VARCHAR(200),
    department_id INTEGER REFERENCES department(id) ON DELETE SET NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_employee_department ON employee(department_id);
CREATE INDEX idx_employee_hire_date ON employee(hire_date);

-- =====================================================================
-- Contracts and histories
-- contract.type values: ESSAI, CDD, CDI, AUTRE
-- contract.sector: AGRI, NON_AGRI
-- =====================================================================
CREATE TABLE contract (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employee(id) ON DELETE CASCADE,
    type VARCHAR(20) NOT NULL,
    sector VARCHAR(20) NOT NULL DEFAULT 'NON_AGRI',
    date_start DATE NOT NULL,
    date_end DATE,
    salary NUMERIC(12,2) DEFAULT 0,
    full_time BOOLEAN DEFAULT TRUE,
    active BOOLEAN DEFAULT TRUE,
    notice_days INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE contract_history (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employee(id) ON DELETE CASCADE,
    contract_id INTEGER REFERENCES contract(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    date_action TIMESTAMP WITH TIME ZONE DEFAULT now(),
    details TEXT
);

CREATE INDEX idx_contract_employee ON contract(employee_id);

-- =====================================================================
-- Documents management (images, pdfs, attestations, contrats signés)
-- file_storage stores metadata; actual files can be stored on disk or object storage
-- =====================================================================
CREATE TABLE document (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employee(id) ON DELETE CASCADE,
    doc_type VARCHAR(100) NOT NULL,
    file_path TEXT NOT NULL,
    file_name VARCHAR(255),
    file_size BIGINT,
    content_type VARCHAR(100),
    uploaded_by INTEGER,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_document_employee ON document(employee_id);

-- =====================================================================
-- Leaves (congés) and workflow + history + planning
-- status: PENDING, APPROVED, REJECTED, CANCELLED
-- =====================================================================
CREATE TABLE leave_request (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employee(id) ON DELETE CASCADE,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days INTEGER NOT NULL,
    leave_type VARCHAR(50) NOT NULL,
    reason TEXT,
    status VARCHAR(20) DEFAULT 'PENDING',
    approver_id INTEGER,
    approved_at TIMESTAMP WITH TIME ZONE,
    justificatif_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE leave_history (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employee(id) ON DELETE CASCADE,
    leave_id INTEGER REFERENCES leave_request(id) ON DELETE SET NULL,
    action VARCHAR(100),
    details TEXT,
    action_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_leave_employee ON leave_request(employee_id);

CREATE OR REPLACE VIEW leave_planning AS
SELECT lr.id, lr.employee_id, e.first_name, e.last_name, lr.start_date, lr.end_date, lr.days, lr.status, lr.leave_type
FROM leave_request lr
JOIN employee e ON e.id = lr.employee_id
WHERE lr.status = 'APPROVED';

-- =====================================================================
-- Absences and rules for repeated unexcused absences
-- =====================================================================
CREATE TABLE absence (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employee(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    reason TEXT,
    justified BOOLEAN DEFAULT FALSE,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_absence_employee_date ON absence(employee_id, date);

-- =====================================================================
-- Presence (daily clock-in/out), minutes late and worked minutes
-- =====================================================================
CREATE TABLE presence (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employee(id) ON DELETE CASCADE,
    work_date DATE NOT NULL,
    time_in TIME,
    time_out TIME,
    minutes_late INTEGER DEFAULT 0,
    worked_minutes INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE (employee_id, work_date)
);

CREATE INDEX idx_presence_employee_date ON presence(employee_id, work_date);

-- =====================================================================
-- Payroll / fiche_paie detailed table
-- contains breakdown: hours (normal, night, sunday, holiday), overtime, gross, deductions, net
-- includes CNAPS & OSTIE breakdown, advances, preavis
-- =====================================================================
CREATE TABLE payroll (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employee(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    salary_base NUMERIC(12,2) DEFAULT 0,
    hours_worked NUMERIC(8,2) DEFAULT 0,
    overtime_hours NUMERIC(8,2) DEFAULT 0,
    hours_night NUMERIC(8,2) DEFAULT 0,
    hours_sunday NUMERIC(8,2) DEFAULT 0,
    hours_holiday NUMERIC(8,2) DEFAULT 0,
    overtime_pay NUMERIC(12,2) DEFAULT 0,
    night_pay NUMERIC(12,2) DEFAULT 0,
    sunday_pay NUMERIC(12,2) DEFAULT 0,
    holiday_pay NUMERIC(12,2) DEFAULT 0,
    gross_salary NUMERIC(14,2) DEFAULT 0,
    cnaps_base NUMERIC(14,2) DEFAULT 0,
    cnaps_employee NUMERIC(14,2) DEFAULT 0,
    cnaps_employer NUMERIC(14,2) DEFAULT 0,
    ostie_employee NUMERIC(14,2) DEFAULT 0,
    ostie_employer NUMERIC(14,2) DEFAULT 0,
    advances NUMERIC(12,2) DEFAULT 0,
    preavis_days INTEGER DEFAULT 0,
    preavis_amount NUMERIC(12,2) DEFAULT 0,
    deductions NUMERIC(14,2) DEFAULT 0,
    net_salary NUMERIC(14,2) DEFAULT 0,
    etat_paie VARCHAR(20) DEFAULT 'MAJ',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE (employee_id, year, month)
);

CREATE INDEX idx_payroll_employee_ym ON payroll(employee_id, year, month);

CREATE TABLE advance (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employee(id) ON DELETE CASCADE,
    amount NUMERIC(12,2) NOT NULL,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    approved BOOLEAN DEFAULT FALSE,
    approved_at TIMESTAMP WITH TIME ZONE,
    month INTEGER,
    year INTEGER,
    note TEXT
);

-- =====================================================================
-- Alerts / notifications
-- =====================================================================
CREATE TABLE alert (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER REFERENCES employee(id) ON DELETE SET NULL,
    alert_type VARCHAR(100),
    message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    status VARCHAR(20) DEFAULT 'OPEN'
);

CREATE INDEX idx_alert_employee ON alert(employee_id);

-- =====================================================================
-- Training budget monitoring
-- =====================================================================
CREATE TABLE training_budget (
    id SERIAL PRIMARY KEY,
    department_id INTEGER REFERENCES department(id) ON DELETE SET NULL,
    year INTEGER NOT NULL,
    budget_amount NUMERIC(14,2) DEFAULT 0,
    spent_amount NUMERIC(14,2) DEFAULT 0
);

CREATE TABLE training_expense (
    id SERIAL PRIMARY KEY,
    department_id INTEGER REFERENCES department(id) ON DELETE SET NULL,
    description TEXT,
    amount NUMERIC(12,2) NOT NULL,
    spent_at DATE DEFAULT now()
);

-- =====================================================================
-- Audit history (generic)
-- =====================================================================
CREATE TABLE audit_history (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER REFERENCES employee(id) ON DELETE SET NULL,
    action VARCHAR(100),
    details TEXT,
    action_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- =====================================================================
-- Reference table for CNAPS/OSTIE rules and SMIG value
-- =====================================================================
CREATE TABLE payroll_config (
    id SERIAL PRIMARY KEY,
    sector VARCHAR(20) UNIQUE,
    hours_per_month NUMERIC(8,2) DEFAULT 173.33,
    cnaps_employee_rate NUMERIC(5,4) DEFAULT 0.01,
    cnaps_employer_rate NUMERIC(5,4) DEFAULT 0.13,
    ostie_employee_rate NUMERIC(5,4) DEFAULT 0.01,
    ostie_employer_rate NUMERIC(5,4) DEFAULT 0.01,
    cnaps_plafond_multiplier NUMERIC(8,2) DEFAULT 8.0 -- multiplier on smig to define plafond
);

CREATE TABLE system_config (
    key TEXT PRIMARY KEY,
    value TEXT
);

INSERT INTO payroll_config (sector, hours_per_month, cnaps_employee_rate, cnaps_employer_rate, ostie_employee_rate, ostie_employer_rate, cnaps_plafond_multiplier)
VALUES
('NON_AGRI', 173.33, 0.01, 0.13, 0.01, 0.01, 8.0),
('AGRI', 200.00, 0.01, 0.08, 0.01, 0.01, 8.0)
ON CONFLICT (sector) DO NOTHING;

INSERT INTO system_config (key, value) VALUES ('SMIG_AMOUNT', '250000') ON CONFLICT DO NOTHING;

-- =====================================================================
-- Utility functions and triggers
-- =====================================================================
CREATE OR REPLACE FUNCTION trg_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF NEW.updated_at IS DISTINCT FROM OLD.updated_at THEN
            NEW.updated_at = now();
        ELSE
            NEW.updated_at = now();
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_employee_updated_at BEFORE UPDATE ON employee FOR EACH ROW EXECUTE FUNCTION trg_set_timestamp();
CREATE TRIGGER trg_contract_updated_at BEFORE UPDATE ON contract FOR EACH ROW EXECUTE FUNCTION trg_set_timestamp();

CREATE OR REPLACE FUNCTION fn_cnaps_base(gross NUMERIC, sector VARCHAR)
RETURNS NUMERIC AS $$
DECLARE
    smig NUMERIC := (SELECT value::NUMERIC FROM system_config WHERE key = 'SMIG_AMOUNT');
    cfg_multiplier NUMERIC := (SELECT cnaps_plafond_multiplier FROM payroll_config WHERE sector = sector LIMIT 1);
    plafond NUMERIC;
BEGIN
    IF cfg_multiplier IS NULL THEN
        cfg_multiplier := 8.0;
    END IF;
    IF smig IS NULL THEN
        smig := 0;
    END IF;
    plafond := smig * cfg_multiplier;
    IF gross > plafond THEN
        RETURN plafond;
    ELSE
        RETURN gross;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_contract_history()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO contract_history(employee_id, contract_id, action, details, date_action)
        VALUES (NEW.employee_id, NEW.id, 'CONTRACT_CREATED', CONCAT('Type=', NEW.type, '; sector=', NEW.sector), now());
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO contract_history(employee_id, contract_id, action, details, date_action)
        VALUES (NEW.employee_id, NEW.id, 'CONTRACT_UPDATED', CONCAT('Old_active=', OLD.active, '->New_active=', NEW.active, '; end=', OLD.date_end, '->', NEW.date_end), now());
        IF OLD.type = 'ESSAI' AND NEW.date_end IS NOT NULL AND NEW.date_end < now()::date THEN
            INSERT INTO alert(employee_id, alert_type, message, created_at, status)
            VALUES (NEW.employee_id, 'ESSAI_EXPIRED', CONCAT('Trial ended on ', NEW.date_end, '. Review contract.'), now(), 'OPEN');
        END IF;
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_contract_history AFTER INSERT OR UPDATE ON contract FOR EACH ROW EXECUTE FUNCTION fn_contract_history();

CREATE OR REPLACE FUNCTION fn_leave_history()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO leave_history(employee_id, leave_id, action, details, action_at)
        VALUES (NEW.employee_id, NEW.id, 'REQUEST_CREATED', CONCAT('From=', NEW.start_date, '; To=', NEW.end_date), now());
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        IF NEW.status IS DISTINCT FROM OLD.status THEN
            INSERT INTO leave_history(employee_id, leave_id, action, details, action_at)
            VALUES (NEW.employee_id, NEW.id, CONCAT('STATUS_', OLD.status, '_TO_', NEW.status), CONCAT('Approver=', NEW.approver_id), now());
        END IF;
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_leave_history AFTER INSERT OR UPDATE ON leave_request FOR EACH ROW EXECUTE FUNCTION fn_leave_history();

-- =====================================================================
-- Views and helper queries for statistics and monitoring
-- =====================================================================
CREATE OR REPLACE VIEW workforce_by_gender AS
SELECT gender_code, COUNT(*) AS headcount
FROM employee
WHERE active = TRUE
GROUP BY gender_code;

CREATE OR REPLACE VIEW avg_age AS
SELECT AVG(EXTRACT(YEAR FROM age(current_date, date_birth)))::NUMERIC(5,2) AS average_age
FROM employee
WHERE date_birth IS NOT NULL AND active = TRUE;

CREATE OR REPLACE VIEW avg_seniority AS
SELECT AVG(EXTRACT(YEAR FROM age(current_date, hire_date)))::NUMERIC(5,2) AS average_seniority
FROM employee
WHERE hire_date IS NOT NULL AND active = TRUE;

CREATE OR REPLACE VIEW turnover_12m AS
SELECT
  (SELECT COUNT(*) FROM employee WHERE termination_date >= (current_date - INTERVAL '12 months'))::NUMERIC AS terminations_12m,
  (SELECT COUNT(*) FROM employee WHERE hire_date >= (current_date - INTERVAL '12 months'))::NUMERIC AS hires_12m,
  (SELECT COUNT(*) FROM employee WHERE active = TRUE)::NUMERIC AS current_headcount;

CREATE OR REPLACE VIEW absenteeism_monthly AS
SELECT date_trunc('month', a.date)::date AS month,
       COUNT(*) AS absence_days,
       (SELECT COUNT(*) FROM employee WHERE active = TRUE) AS headcount
FROM absence a
GROUP BY date_trunc('month', a.date);

CREATE OR REPLACE VIEW unused_leave_summary AS
SELECT e.id AS employee_id, e.matricule, e.first_name, e.last_name,
       COALESCE(SUM(lr.days) FILTER (WHERE lr.status = 'APPROVED'),0) AS total_approved,
       COALESCE((SELECT COUNT(*) FROM absence a2 WHERE a2.employee_id = e.id),0) AS unauthorized_absences
FROM employee e
LEFT JOIN leave_request lr ON lr.employee_id = e.id
GROUP BY e.id, e.matricule, e.first_name, e.last_name;

CREATE OR REPLACE FUNCTION fn_check_hr_alerts()
RETURNS VOID AS $$
DECLARE
    rec RECORD;
BEGIN
    FOR rec IN SELECT lr.id, lr.employee_id, lr.end_date FROM leave_request lr WHERE lr.status = 'APPROVED' AND lr.end_date < current_date LOOP
        IF NOT EXISTS (SELECT 1 FROM presence p WHERE p.employee_id = rec.employee_id AND p.work_date >= rec.end_date) THEN
            INSERT INTO alert(employee_id, alert_type, message, created_at, status)
            VALUES (rec.employee_id, 'NO_RETURN_FROM_LEAVE', CONCAT('Employee did not return from leave expected on ', rec.end_date), now(), 'OPEN')
            ON CONFLICT DO NOTHING;
        END IF;
    END LOOP;

    FOR rec IN SELECT a.employee_id, COUNT(*) AS cnt FROM absence a WHERE a.justified = FALSE AND a.date >= (current_date - INTERVAL '30 days') GROUP BY a.employee_id HAVING COUNT(*) > 3 LOOP
        INSERT INTO alert(employee_id, alert_type, message, created_at, status)
        VALUES (rec.employee_id, 'REPEATED_ABSENCE', CONCAT('Repeated unexcused absences in last 30 days: ', rec.cnt), now(), 'OPEN') ON CONFLICT DO NOTHING;
    END LOOP;

    FOR rec IN SELECT tb.id, tb.department_id, tb.year, tb.spent_amount, tb.budget_amount FROM training_budget tb WHERE tb.spent_amount > tb.budget_amount LOOP
        INSERT INTO alert(employee_id, alert_type, message, created_at, status)
        VALUES (NULL, 'TRAINING_BUDGET_OVERRUN', CONCAT('Department ', rec.department_id, ' exceeded training budget for year ', rec.year), now(), 'OPEN') ON CONFLICT DO NOTHING;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- Function to generate payroll for one employee (basic computation)
-- This function computes gross/net based on contract salary, CNAPS/OSTIE rates
-- and stores/updates a row in payroll table. It is intentionally simple and
-- should be extended to incorporate night/sunday/holiday hours and overtime.
-- =====================================================================
CREATE OR REPLACE FUNCTION fn_generate_payroll(p_employee_id INTEGER, p_year INTEGER, p_month INTEGER)
RETURNS VOID AS $$
DECLARE
    v_contract RECORD;
    v_sector VARCHAR := 'NON_AGRI';
    v_salary NUMERIC := 0;
    v_hours_per_month NUMERIC := 173.33;
    v_cnaps_emp_rate NUMERIC := 0.01;
    v_cnaps_er_rate NUMERIC := 0.13;
    v_ostie_emp_rate NUMERIC := 0.01;
    v_ostie_er_rate NUMERIC := 0.01;
    v_cnaps_base NUMERIC := 0;
    v_cnaps_employee NUMERIC := 0;
    v_cnaps_employer NUMERIC := 0;
    v_ostie_employee NUMERIC := 0;
    v_ostie_employer NUMERIC := 0;
    v_advances NUMERIC := 0;
    v_gross NUMERIC := 0;
    v_deductions NUMERIC := 0;
    v_net NUMERIC := 0;
BEGIN
    -- get active contract if any (most recent)
    SELECT * INTO v_contract FROM contract WHERE employee_id = p_employee_id AND active = TRUE ORDER BY date_start DESC LIMIT 1;
    IF FOUND THEN
        v_salary := COALESCE(v_contract.salary, 0);
        v_sector := COALESCE(v_contract.sector, 'NON_AGRI');
    ELSE
        SELECT salary_base INTO v_salary FROM employee WHERE id = p_employee_id;
    END IF;

    -- get payroll config for sector
    SELECT hours_per_month, cnaps_employee_rate, cnaps_employer_rate, ostie_employee_rate, ostie_employer_rate
    INTO v_hours_per_month, v_cnaps_emp_rate, v_cnaps_er_rate, v_ostie_emp_rate, v_ostie_er_rate
    FROM payroll_config WHERE sector = v_sector LIMIT 1;

    IF v_hours_per_month IS NULL THEN
        v_hours_per_month := 173.33;
    END IF;

    v_gross := COALESCE(v_salary,0);

    -- CNAPS base with plafond
    v_cnaps_base := fn_cnaps_base(v_gross, v_sector);
    v_cnaps_employee := round((v_cnaps_base * v_cnaps_emp_rate)::numeric,2);
    v_cnaps_employer := round((v_cnaps_base * v_cnaps_er_rate)::numeric,2);

    v_ostie_employee := round((v_gross * v_ostie_emp_rate)::numeric,2);
    v_ostie_employer := round((v_gross * v_ostie_er_rate)::numeric,2);

    -- advances for this month/year
    SELECT COALESCE(SUM(amount),0) INTO v_advances FROM advance WHERE employee_id = p_employee_id AND approved = TRUE AND month = p_month AND year = p_year;

    v_deductions := COALESCE(v_cnaps_employee,0) + COALESCE(v_ostie_employee,0) + COALESCE(v_advances,0);
    v_net := round((v_gross - v_deductions)::numeric,2);

    -- upsert into payroll table
    INSERT INTO payroll(employee_id, year, month, salary_base, hours_worked, overtime_hours, hours_night, hours_sunday, hours_holiday,
                         overtime_pay, night_pay, sunday_pay, holiday_pay, gross_salary, cnaps_base, cnaps_employee, cnaps_employer,
                         ostie_employee, ostie_employer, advances, deductions, net_salary, etat_paie, created_at)
    VALUES (p_employee_id, p_year, p_month, v_salary, 0, 0, 0, 0, 0, 0, 0, 0, 0, v_gross, v_cnaps_base, v_cnaps_employee, v_cnaps_employer,
            v_ostie_employee, v_ostie_employer, v_advances, v_deductions, v_net, 'MAJ', now())
    ON CONFLICT (employee_id, year, month) DO UPDATE
    SET salary_base = EXCLUDED.salary_base,
        gross_salary = EXCLUDED.gross_salary,
        cnaps_base = EXCLUDED.cnaps_base,
        cnaps_employee = EXCLUDED.cnaps_employee,
        cnaps_employer = EXCLUDED.cnaps_employer,
        ostie_employee = EXCLUDED.ostie_employee,
        ostie_employer = EXCLUDED.ostie_employer,
        advances = EXCLUDED.advances,
        deductions = EXCLUDED.deductions,
        net_salary = EXCLUDED.net_salary,
        etat_paie = EXCLUDED.etat_paie,
        created_at = now();

END;
$$ LANGUAGE plpgsql;

-- Indexes for reporting
CREATE INDEX idx_leave_start ON leave_request(start_date);
CREATE INDEX idx_payroll_year_month ON payroll(year, month);

-- =====================================================================
-- End of extended base2.sql
-- Notes: See comments in the schema for how to integrate payroll computation and scheduled jobs.

