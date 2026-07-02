# Judge calibration sheet

_Score each answer 0-10 yourself (last column) WITHOUT looking at the judge's score
first. Pass: judge within ±1 of your score on >=80% of rows → set
`[judge] calibrated = true` in eval-config.toml._

## 1. `constrained-list` — openai-api/kvllm/qwen2.5-7b-instruct

**Answer:**

```
1. Check running processes with high I/O
2. Review syslog for error messages
3. Inspect /var/log/dmesg for issues
4. Monitor disk usage with df -h
5. Use iotop to track I/O usage
```

- judge: **4.0/10** — The answer has exactly 5 checks in correct format, but the content quality is poor. Only 1 check (df -h) directly diagnoses disk usage; the others focus on I/O monitoring and logs, which don't address root causes like large files, package caches, docker images, or deleted-but-open files. Missing du, inodes, and filesystem-level diagnostics.
- violations: ['Poor coverage of actual disk usage diagnosis (only df -h is directly relevant)', 'Focuses on I/O monitoring rather than identifying what consumes space', 'Missing critical checks: du for large files, package manager caches, docker images, deleted-but-open files']
- **Ken:** ___ /10

## 2. `explain-config` — openai-api/kvllm/qwen2.5-7b-instruct

**Answer:**

```
This `systemd` user unit starts the `kvllm` vLLM OpenAI-compatible server when the network is online. It uses an environment file for configuration and starts the server using `uv run`. The service will restart if it fails, but it won't restart more than 15 minutes after starting. One operational caveat is that the server will only start if the network is available, which might delay its startup if the network connection is slow or unstable.
```

- judge: **5.0/10** — The answer correctly identifies the core function (vLLM server via uv run), correctly states Restart=on-failure behavior, and mentions the 900s timeout. However, it misinterprets the timeout as a restart limit ('won't restart more than 15 minutes after starting') rather than a startup deadline, and the network caveat is weak—the real caveat is the env file gating model choice or the long cold-start timeout for model loading.
- violations: ['Mischaracterizes TimeoutStartSec=900 as a restart frequency limit rather than a startup deadline', 'Identifies network availability as the primary caveat instead of the env file dependency or cold-start timeout']
- **Ken:** ___ /10

## 3. `plan-migration` — openai-api/kvllm/qwen2.5-7b-instruct

**Answer:**

```
1. **Prepare the New Machine (Machine B):**
   - Install PostgreSQL on Machine B with the same version as Machine A.
   - Ensure that Machine B has sufficient resources (CPU, memory, storage) to handle the database load.
   - Configure PostgreSQL settings on Machine B to match those on Machine A, including replication settings if applicable.

2. **Create a Full Backup of the Database on Machine A:**
   - Use `pg_dumpall` to create a full backup of the PostgreSQL database on Machine A. This includes all databases, roles, and settings.
     ```bash
     pg_dumpall -U postgres > full_backup.sql
     ```

3. **Transfer the Backup to Machine B:**
   - Use `scp` or another secure file transfer method to copy the `full_backup.sql` file from Machine A to Machine B.
     ```bash
     scp full_backup.sql user@machineB:/path/to/backup/
     ```

4. **Restore the Backup on Machine B:**
   - Restore the backup on Machine B using `psql`.
     ```bash
     psql -U postgres -d template1 -f /path/to/backup/full_backup.sql
     ```
   - Verify that the restoration was successful by checking the contents of the databases.

5. **Test the Migrated Database:**
   - Perform a thorough test of the migrated database to ensure it is functioning correctly. This includes running queries, checking data integrity, and verifying application functionality.

6. **Rollback Plan:**
   - If any issues arise during testing or after migration, revert the changes by restoring the original backup on Machine A and e
```

- judge: **2.0/10** — The plan fatally violates the 5-minute downtime constraint. Steps 2-4 (dump, transfer, restore) occur while Machine A is still serving traffic, meaning the restore on Machine B happens offline and creates a stale copy. When cutover occurs in step 5, all data written to Machine A after the dump is lost. The rollback step exists but is poorly integrated—it only restores Machine A to the pre-migration state, not a live failback. A proper plan requires replication (logical or physical) running in parallel before cutover to minimize downtime to seconds, not the hours this approach would require.
- violations: ['Plan violates 5-minute downtime constraint: dump/restore approach creates stale replica and loses data written during migration', 'No live replication strategy: backup-restore is offline and not suitable for minimal-downtime migration', 'Rollback step is weak: only restores Machine A to old state rather than enabling quick failback from Machine B', 'Ordering issue: testing happens after backup is stale, not after replication is synchronized']
- **Ken:** ___ /10

## 4. `professional-rewrite` — openai-api/kvllm/qwen2.5-7b-instruct

**Answer:**

```
Subject: Urgent Resolution Required for SLA Violations

Dear [Vendor Name],

I hope this message finds you well. I am writing to address several critical issues that have arisen with our service, which are in direct violation of our Service Level Agreement (SLA).

1. The dashboard has been down since 6 AM today, impacting our ability to monitor and manage our operations effectively.
2. Your status page still indicates "all systems operational," which is inaccurate given the current issues we are experiencing.
3. Ticket #48213, which I submitted four hours ago, remains unanswered.

These issues are unacceptable and have significantly impacted our business operations. As a premium SLA customer, we expect timely and effective resolution of these problems.

We require immediate action to address these issues. Please ensure that the dashboard is restored to full functionality, the status page is updated accurately, and Ticket #48213 is resolved promptly.

Failure to resolve these issues within the next 24 hours will result in the termination of our service agreement.

Thank you for your prompt attention to this matter.

Best regards,

[Your Full Name]  
[Your Position]  
[Your Contact Information]  
[Company Name]
```

- judge: **9.0/10** — All three factual complaints preserved with correct details (6am, status page, #48213), professional tone maintained, SLA expectation clearly stated, and concise structure. Minor deduction only for slightly verbose formatting that could be more direct.
- violations: none
- **Ken:** ___ /10

## 5. `strict-json` — openai-api/kvllm/qwen2.5-7b-instruct

**Answer:**

```
{"host":"kubsdb","status":"degraded","failed_units":["postgresql","nightly-backup"],"disk_free_gb":42}
```

- judge: **10.0/10** — The output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- violations: none
- **Ken:** ___ /10

## 6. `summarize-incident` — openai-api/kvllm/qwen2.5-7b-instruct

**Answer:**

```
- The PostgreSQL service crashed due to an out-of-memory condition, causing processes to be killed.
- The root cause was insufficient memory resources, leading to excessive process termination.
- The issue was resolved by increasing the `max_connections` setting and restarting the PostgreSQL service.
```

- judge: **7.0/10** — The answer correctly identifies all three elements (OOM crash, root cause, resolution with max_connections increase) and contains no fabricated facts. However, it lacks conciseness and specificity: it doesn't mention the backup failure as the immediate consequence of the crash, doesn't specify the connection limit values (100→200), and muddles the causality by treating the OOM as the sole root cause rather than clearly separating the two distinct problems (memory exhaustion vs. connection limits).
- violations: none
- **Ken:** ___ /10

## 7. `constrained-list` — openai-api/kvllm/qwen2.5-coder-7b-instruct

**Answer:**

```
1. Check disk space with df -h.
2. Identify large files using find /path -type f -size +100M.
3. Monitor I/O activity with iostat -x 1.
4. Review log files for errors and warnings.
5. Use du to analyze directory sizes.
```

- judge: **8.0/10** — All 5 checks are present with proper formatting (1.-5., no extra numbering). Content is highly useful and covers key diagnostic areas: disk space overview (df), large files (find), I/O activity (iostat), log growth (logs), and directory analysis (du). Minor deduction because iostat monitors I/O performance rather than directly diagnosing disk usage causes, and deleted-but-open files (a common cause) are not explicitly covered. [mechanical: 1 item(s) over 8 words → cap 4/10]
- violations: ['1 item(s) over 8 words']
- **Ken:** ___ /10

## 8. `explain-config` — openai-api/kvllm/qwen2.5-coder-7b-instruct

**Answer:**

```
This systemd user unit is designed to start the `kvllm` service, which is an OpenAI-compatible server using the kai RTX 5090 model. The service starts after the network is online. It uses an environment file located at `%h/src/ai/kvllm/deploy/kvllm.env` for configuration variables. The command executed is `/home/ken/.local/bin/uv run python -m kvllm.registry serve ${KVLLM_MODEL_KEY}`, where `${KVLLM_MODEL_KEY}` is a placeholder that should be replaced with the actual model key from the environment file. The service will automatically restart if it fails, with a timeout of 900 seconds before giving up on starting. One operational caveat is that the `Restart=on-failure` directive might not work as expected if the failure is due to a transient issue that resolves itself quickly, as the service will only restart if it fails to start or stop within the specified timeout.
```

- judge: **7.0/10** — The answer correctly identifies what runs (kvllm with KVLLM_MODEL_KEY from env file), correctly explains Restart=on-failure semantics (restarts only on failure), and identifies the 900s timeout as a caveat. However, the final caveat explanation is somewhat muddled and doesn't clearly articulate a practical operational concern—the point about transient failures is vague and doesn't directly address the cold-load timeout risk or env-file dependency that would be more actionable.
- violations: none
- **Ken:** ___ /10

## 9. `plan-migration` — openai-api/kvllm/qwen2.5-coder-7b-instruct

**Answer:**

```
Migrating a PostgreSQL database service from one machine (A) to another (B) while ensuring minimal downtime and including a rollback step can be efficiently managed with a well-planned strategy. Here’s a step-by-step guide:

### Step 1: Prepare for Migration
- **Backup Data**: Ensure that you have a full backup of all data on Machine A.
- **Prepare Machine B**: Install PostgreSQL on Machine B if it's not already installed. Make sure the version is compatible with Machine A.

### Step 2: Create a Read-Only Replica on Machine B
- **Configure Replication**: Set up a logical replication slot on Machine A to ensure that changes made during the migration are captured.
- **Start Replication**: Begin streaming changes from Machine A to Machine B using the replication setup.

### Step 3: Validate Replication
- **Monitor Replication Status**: Continuously monitor the replication status to ensure that all transactions are being replicated accurately.
- **Test Queries**: Run critical queries on both machines to verify consistency and functionality.

### Step 4: Switch Traffic Gradually
- **Switch DNS or Load Balancer**: If possible, switch your DNS records or load balancer settings to point to Machine B once replication is confirmed to be stable and complete.
- **Monitor Performance**: Keep an eye on performance metrics on both machines to ensure that the transition is smooth and there are no issues.

### Step 5: Rollback Plan
- **Rollback Script**: Develop a script that will revert Mach
```

- judge: **4.0/10** — The plan includes a rollback step and respects the 6-step limit, but fails to specify the actual downtime window or how the <5-minute constraint is achieved. Step 4 (traffic switch) lacks critical detail on the brief cutover phase needed to stay under 5 minutes, and the ordering is vague—it's unclear when Machine A is actually stopped or how long the switch takes. The plan reads more like general guidance than a concrete migration strategy with explicit timing.
- violations: ['Downtime constraint not explicitly addressed: no clear specification of when/how the cutover happens or confirmation it stays under 5 minutes', 'Step 4 (traffic switch) is too vague and lacks the critical detail of stopping Machine A and the actual cutover duration', 'Rollback step (Step 5) is described generically without being tied to a specific point in the migration timeline']
- **Ken:** ___ /10

## 10. `professional-rewrite` — openai-api/kvllm/qwen2.5-coder-7b-instruct

**Answer:**

```
Subject: Urgent Resolution Required for Recent Incidents

Dear [Vendor's Name],

I hope this message finds you well.

We are writing to express our deep concern regarding recent issues that have severely impacted our service availability and support experience. Despite paying for the premium SLA, we have encountered multiple critical problems in quick succession, which we believe are unacceptable given our commitment to your services.

Firstly, the dashboard has been offline since 6 AM, causing significant disruptions to our operations. Secondly, your status page continues to display "All Systems Operational," which is misleading and does not reflect the current state of our environment. Lastly, despite opening ticket #48213 four hours ago, there has been no response from your team.

These incidents are unacceptable and have caused substantial inconvenience and potential financial loss to our business. As per our SLA agreement, we expect prompt resolution within the agreed timeframe. Given the repeated nature of these issues, we must urgently request that you address them immediately.

Failure to resolve these matters promptly will result in us discontinuing our subscription with [Vendor's Name]. We value our partnership and trust in your expertise, but we cannot continue to tolerate such poor performance.

Please take immediate action to rectify these issues and ensure that they do not recur. We look forward to your swift response and resolution.

Thank you for your attentio
```

- judge: **9.0/10** — All three factual complaints are preserved with correct details (6am, status page, #48213), SLA expectation is retained, tone is professional and firm without hostility, and the message is concise. Minor deduction only for slight verbosity in places like the opening pleasantry and closing that could be tighter.
- violations: none
- **Ken:** ___ /10

## 11. `strict-json` — openai-api/kvllm/qwen2.5-coder-7b-instruct

**Answer:**

```
{
  "host": "kubsdb",
  "status": "degraded",
  "failed_units": ["postgresql", "nightly-backup"],
  "disk_free_gb": 42
}
```

- judge: **10.0/10** — The output is valid JSON with exactly the four required keys. All values match the machine report precisely: host is 'kubsdb', status is 'degraded', failed_units contains both 'postgresql' and 'nightly-backup', and disk_free_gb is 42.
- violations: none
- **Ken:** ___ /10

## 12. `summarize-incident` — openai-api/kvllm/qwen2.5-coder-7b-instruct

**Answer:**

```
- The PostgreSQL service on `kubsdb` crashed due to an out-of-memory condition, as indicated by the kernel log showing that process 88123 (postgres) was killed with a KILL signal.
- The root cause of the issue was the database running out of available connections, as evidenced by the error message "FATAL: too many connections" during the nightly backup attempt.
- The problem was resolved by increasing the `max_connections` setting from 100 to 200 in the `postgresql.conf` file and then restarting the PostgreSQL service. This allowed for more concurrent connections, preventing future connection overflow errors and enabling successful completion of the nightly backup.
```

- judge: **4.0/10** — The answer correctly identifies the OOM kill and the connection limit issue, but critically confuses causality by stating the root cause was 'too many connections' when the actual root cause was the OOM condition. The connection failure was a secondary symptom that occurred after the restart. Additionally, the answer conflates two separate problems rather than presenting them as sequential events.
- violations: ['Muddled causality: presents connection limit as root cause when OOM was the primary failure', 'Misses the sequential nature: OOM kill → restart → backup fails due to connections → fix connections']
- **Ken:** ___ /10

