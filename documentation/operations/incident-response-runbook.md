# Janus Incident Response Runbook

## Overview

This runbook provides step-by-step procedures for responding to incidents in the Janus multi-agent AI system. It covers everything from minor issues to critical system failures, including security incidents, performance degradation, and service outages.

## Table of Contents

1. [Incident Classification](#incident-classification)
2. [Response Team Structure](#response-team-structure)
3. [Communication Protocols](#communication-protocols)
4. [Severity-Specific Procedures](#severity-specific-procedures)
5. [Security Incident Response](#security-incident-response)
6. [Performance Incident Response](#performance-incident-response)
7. [Infrastructure Incident Response](#infrastructure-incident-response)
8. [Data Recovery Procedures](#data-recovery-procedures)
9. [Post-Incident Review](#post-incident-review)
10. [Emergency Contacts](#emergency-contacts)

---

## Incident Classification

### Severity Levels

#### P0 - Critical
- **Definition**: Complete service outage, data breach, security compromise
- **Response Time**: 15 minutes
- **Escalation**: Immediate executive notification
- **Examples**:
  - All services down
  - Database corruption
  - Active security breach
  - Data loss

#### P1 - High
- **Definition**: Major functionality affected, significant performance degradation
- **Response Time**: 1 hour
- **Escalation**: Management notification within 2 hours
- **Examples**:
  - Core services unavailable
  - Major performance degradation (>50% response time increase)
  - Partial data loss
  - Authentication system failure

#### P2 - Medium
- **Definition**: Minor functionality affected, moderate performance impact
- **Response Time**: 4 hours
- **Escalation**: Team lead notification
- **Examples**:
  - Non-critical services down
  - Minor performance degradation (20-50%)
  - Individual component failures
  - Minor security issues

#### P3 - Low
- **Definition**: Cosmetic issues, minimal impact
- **Response Time**: 24 hours
- **Escalation**: Standard ticket handling
- **Examples**:
  - UI glitches
  - Documentation errors
  - Minor logging issues
  - Performance degradation <20%

### Incident Categories

1. **Security**: Data breaches, unauthorized access, malware
2. **Performance**: Slow response times, high resource usage
3. **Infrastructure**: Server failures, network issues, storage problems
4. **Application**: Code bugs, service crashes, logic errors
5. **Data**: Database corruption, backup failures, data loss
6. **Third-party**: External service outages, API failures

---

## Response Team Structure

### Primary Roles

#### Incident Commander (IC)
- **Responsibility**: Overall incident coordination
- **Authority**: Makes all decisions during incident
- **Communication**: Primary contact for stakeholders
- **Duration**: Remains in role until incident resolved

#### Technical Lead (TL)
- **Responsibility**: Technical investigation and resolution
- **Authority**: Technical decision making
- **Focus**: Root cause analysis and fix implementation
- **Handoff**: Briefs IC on technical findings

#### Communications Lead (CL)
- **Responsibility**: Internal and external communications
- **Authority**: All official communications
- **Focus**: Status updates, stakeholder notifications
- **Coordination**: Works closely with IC

#### Scribe (S)
- **Responsibility**: Documentation and timeline
- **Authority**: Official incident record
- **Focus**: Detailed logging of all actions
- **Output**: Complete incident timeline

### Escalation Matrix

```
┌─────────────────────────────────────────────────────────────┐
│                        ESCALATION MATRIX                    │
├─────────────────┬──────────────┬────────────────────────────┤
│ Severity        │ Time to Escalate │ Who to Notify          │
├─────────────────┼──────────────┼────────────────────────────┤
│ P0 - Critical   │ 15 minutes   │ CEO, CTO, VP Engineering   │
│ P1 - High       │ 1 hour       │ Engineering Manager, VP    │
│ P2 - Medium     │ 4 hours      │ Team Lead, Manager         │
│ P3 - Low        │ 24 hours     │ Team Lead                  │
└─────────────────┴──────────────┴────────────────────────────┘
```

---

## Communication Protocols

### Communication Channels

#### Internal Channels
1. **Slack**: #incident-response (primary)
2. **Video Call**: Google Meet (emergency)
3. **Phone**: On-call rotation (critical only)
4. **Email**: incident-response@company.com

#### External Channels
1. **Status Page**: status.janus-ai.com
2. **Customer Email**: support@janus-ai.com
3. **Social Media**: @JanusAI (if applicable)
4. **Press Release**: PR team coordination

### Communication Templates

#### Initial Alert Template
```
🚨 INCIDENT ALERT - [SEVERITY] 🚨

Incident ID: INC-YYYY-MM-DD-NNN
Severity: [P0/P1/P2/P3]
Status: Investigating
Start Time: [TIME]

Summary: [Brief description]
Impact: [Affected services/users]
Current Actions: [What's being done]
Next Update: [When]

Incident Commander: [Name]
Slack Channel: #incident-[ID]
```

#### Status Update Template
```
📊 STATUS UPDATE - [TIME] 📊

Incident ID: INC-YYYY-MM-DD-NNN
Severity: [P0/P1/P2/P3]
Status: [Investigating/Identified/Fixing/Monitoring/Resolved]
Duration: [X hours Y minutes]

Progress:
✅ [Completed actions]
🔄 [In-progress actions]
⏳ [Planned actions]

Impact Update: [Current impact]
Next Update: [When]
```

#### Resolution Template
```
✅ INCIDENT RESOLVED ✅

Incident ID: INC-YYYY-MM-DD-NNN
Severity: [P0/P1/P2/P3]
Status: RESOLVED
Duration: [Total duration]
Resolution Time: [When resolved]

Summary: [What happened]
Root Cause: [Root cause]
Resolution: [How fixed]
Impact: [Final impact assessment]

Next Steps:
- Post-mortem: [When]
- Follow-up actions: [List]
- Preventive measures: [List]

Thank you for your patience.
```

---

## Severity-Specific Procedures

### P0 - Critical Incident Response

#### Immediate Actions (0-15 minutes)
1. **Alert Team**
   ```bash
   # Send emergency alert
   python scripts/send_emergency_alert.py \
     --severity P0 \
     --message "Critical incident detected" \
     --services "all"
   ```

2. **Establish Command**
   - Designate Incident Commander
   - Create Slack channel: #incident-[ID]
   - Start incident timer
   - Begin documentation

3. **Assess Impact**
   ```bash
   # Check system health
   curl -sf http://localhost:8000/api/v1/system/status
   
   # Check service health
   curl -sf http://localhost:8000/api/v1/system/health/services
   
   # Check user impact
   python scripts/assess_user_impact.py --severity P0
   ```

4. **Preserve Evidence**
   ```bash
   # Create system snapshot
   docker exec janus_api sh -c "
     mkdir -p /tmp/incident-evidence/$(date +%Y%m%d_%H%M%S) &&
     cp -r /app/logs /tmp/incident-evidence/$(date +%Y%m%d_%H%M%S)/ &&
     cp -r /var/log /tmp/incident-evidence/$(date +%Y%m%d_%H%M%S)/
   "
   
   # Export system metrics
   curl -sf http://localhost:8000/api/v1/observability/metrics/summary \
     > evidence/metrics_$(date +%Y%m%d_%H%M%S).json
   ```

#### Investigation Phase (15-60 minutes)
1. **Gather Information**
   ```bash
   # Check recent deployments
   git log --oneline --since="2 hours ago"
   
   # Check Docker status
   docker compose -f docker-compose.pc1.yml ps
   docker compose -f docker-compose.pc2.yml ps
   
   # Check logs
   docker compose -f docker-compose.pc1.yml logs --tail=100 janus-api
   ```

2. **Isolate Affected Systems**
   ```bash
   # If security incident, isolate services
   docker compose -f docker-compose.pc1.yml stop janus-api
   
   # If data corruption, stop writes
   docker exec postgres psql -c "
     ALTER DATABASE janus SET default_transaction_read_only = on;
   "
   ```

3. **Notify Stakeholders**
   - Executive team (immediate)
   - Major customers (within 30 minutes)
   - Regulatory bodies (if required)

#### Resolution Phase (1-4 hours)
1. **Implement Fix**
   - Deploy hotfix if available
   - Rollback to last known good state
   - Implement temporary workaround

2. **Verify Resolution**
   ```bash
   # Run health checks
   python tooling/dev.py doctor
   
   # Test critical endpoints
   python test_scenario1_apis.py
   
   # Monitor for 30 minutes
   watch -n 30 'curl -sf http://localhost:8000/health'
   ```

3. **Communication**
   - Send resolution notice
   - Schedule post-mortem
   - Update status page

### P1 - High Incident Response

#### Immediate Actions (0-1 hour)
1. **Alert Team**
   - Notify on-call engineer
   - Create incident channel
   - Assign roles

2. **Assess Impact**
   ```bash
   # Check affected services
   python scripts/check_service_health.py --severity P1
   
   # Check performance metrics
   curl "http://localhost:8000/api/v1/observability/slo/domains?window_minutes=60"
   ```

3. **Begin Investigation**
   - Check recent changes
   - Review error logs
   - Identify affected components

#### Investigation Phase (1-4 hours)
1. **Detailed Analysis**
   ```bash
   # Check specific service health
   curl -sf http://localhost:8000/api/v1/system/health/services
   
   # Review performance metrics
   python tooling/generate_api_coverage_report.py \
     --collect-docker-evidence \
     --docker-evidence-json evidence/docker_p1.json
   ```

2. **Implement Temporary Fix**
   - Scale up affected services
   - Enable circuit breakers
   - Implement rate limiting

3. **Monitor Progress**
   - Track resolution progress
   - Update stakeholders hourly

### P2 - Medium Incident Response

#### Response Actions (0-4 hours)
1. **Initial Assessment**
   - Review monitoring alerts
   - Check service logs
   - Determine impact scope

2. **Investigation**
   ```bash
   # Check specific components
   docker compose -f docker-compose.pc1.yml logs [service-name]
   
   # Review recent changes
   git log --oneline --since="24 hours ago"
   ```

3. **Resolution**
   - Implement fix or workaround
   - Test solution
   - Monitor for stability

### P3 - Low Incident Response

#### Response Actions (0-24 hours)
1. **Standard Ticket Handling**
   - Create tracking ticket
   - Assign to appropriate team
   - Schedule for next sprint if needed

2. **Investigation**
   - Review logs when convenient
   - Identify root cause
   - Plan fix implementation

---

## Security Incident Response

### Data Breach Response

#### Immediate Actions (0-15 minutes)
1. **Containment**
   ```bash
   # Isolate affected systems
   docker compose -f docker-compose.pc1.yml stop janus-api
   
   # Block suspicious IPs
   python scripts/block_ips.py --file suspicious_ips.txt
   
   # Preserve evidence
   docker commit janus_api incident-evidence:$(date +%Y%m%d_%H%M%S)
   ```

2. **Assessment**
   ```bash
   # Check access logs
   grep -i "unauthorized\|failed\|error" /var/log/janus/access.log
   
   # Review authentication logs
   docker exec janus_api grep -i "auth\|login" /app/logs/security.log
   ```

3. **Notification**
   - Legal team (immediate)
   - Executive team (immediate)
   - Affected users (within 72 hours per GDPR)

#### Investigation Phase (15 minutes - 4 hours)
1. **Evidence Collection**
   ```bash
   # Export security logs
   docker exec janus_api tar -czf /tmp/security_logs.tar.gz /app/logs/
   
   # Check database for unauthorized access
   docker exec postgres psql -c "
     SELECT * FROM audit_log 
     WHERE action_time > NOW() - INTERVAL '2 hours'
     AND action_type IN ('login', 'data_access', 'data_export')
   "
   ```

2. **Scope Assessment**
   - Number of affected users
   - Types of data accessed
   - Duration of exposure
   - Potential impact

3. **Remediation**
   - Reset affected user passwords
   - Revoke compromised tokens
   - Patch security vulnerabilities

#### Recovery Phase (4-24 hours)
1. **System Restoration**
   - Verify system integrity
   - Restore from clean backups
   - Implement additional security measures

2. **Communication**
   - Notify regulatory authorities
   - Communicate with affected users
   - Provide guidance on protective measures

### Ransomware Response

#### Immediate Actions
1. **Isolation**
   ```bash
   # Disconnect from network
   docker network disconnect bridge janus_api
   
   # Stop all services
   docker compose -f docker-compose.pc1.yml down
   docker compose -f docker-compose.pc2.yml down
   ```

2. **Assessment**
   - Determine encryption scope
   - Identify ransomware variant
   - Check backup integrity

3. **Decision Making**
   - Pay ransom (generally not recommended)
   - Restore from backups
   - Attempt decryption

#### Recovery Procedures
1. **Clean Restoration**
   ```bash
   # Wipe infected systems
   docker system prune -a
   
   # Restore from clean backups
   python scripts/restore_from_backup.py --date [backup-date]
   
   # Verify integrity
   python tooling/dev.py doctor
   ```

2. **Enhanced Security**
   - Implement additional monitoring
   - Update security policies
   - Conduct security audit

---

## Performance Incident Response

### High Response Time Incident

#### Detection and Assessment
```bash
# Check current response times
curl "http://localhost:8000/api/v1/observability/slo/domains?window_minutes=15"

# Check resource utilization
docker stats --no-stream

# Check database performance
docker exec postgres psql -c "
  SELECT 
    schemaname,
    tablename,
    n_tup_ins + n_tup_upd + n_tup_del as total_changes,
    n_live_tup as live_tuples
  FROM pg_stat_user_tables 
  ORDER BY total_changes DESC
"
```

#### Investigation Steps
1. **Identify Bottlenecks**
   ```bash
   # Check slow queries
   docker exec postgres psql -c "
     SELECT 
       query,
       calls,
       total_time,
       mean_time
     FROM pg_stat_statements
     WHERE mean_time > 1000
     ORDER BY mean_time DESC
     LIMIT 10
   "
   
   # Check API endpoints
   curl "http://localhost:8000/api/v1/observability/metrics/summary"
   ```

2. **Resource Analysis**
   ```bash
   # Memory usage
   free -h
   
   # CPU usage
   top -b -n 1 | head -20
   
   # Disk usage
   df -h
   
   # Network connections
   netstat -tuln | grep :8000
   ```

#### Resolution Actions
1. **Immediate Relief**
   ```bash
   # Restart services
   docker compose -f docker-compose.pc1.yml restart janus-api
   
   # Clear caches
   docker exec redis redis-cli FLUSHALL
   
   # Scale up services
   docker compose -f docker-compose.pc1.yml up -d --scale janus-api=3
   ```

2. **Database Optimization**
   ```bash
   # Update statistics
   docker exec postgres psql -c "VACUUM ANALYZE;"
   
   # Check for locks
   docker exec postgres psql -c "
     SELECT 
       blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user
     FROM pg_catalog.pg_locks blocked_locks
     JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
     JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
     JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
     WHERE NOT blocked_locks.granted
   "
   ```

### Memory Leak Incident

#### Detection
```bash
# Monitor memory usage over time
watch -n 30 'docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"'

# Check for memory leaks in logs
docker compose -f docker-compose.pc1.yml logs janus-api | grep -i "memory\|leak\|oom"
```

#### Investigation
1. **Application Analysis**
   ```bash
   # Generate heap dump (if JVM-based)
   docker exec janus_api jmap -dump:format=b,file=/tmp/heap.hprof [PID]
   
   # Check Python memory usage
   docker exec janus_api python -c "
   import gc
   import psutil
   print(f'Memory: {psutil.virtual_memory().percent}%')
   gc.collect()
   print(f'Garbage collected: {gc.get_count()}')
   "
   ```

2. **Database Analysis**
   ```bash
   # Check connection pooling
   docker exec postgres psql -c "
     SELECT count(*), state 
     FROM pg_stat_activity 
     GROUP BY state
   "
   
   # Check memory usage
   docker exec postgres psql -c "
     SELECT 
       name,
       setting,
       unit
     FROM pg_settings
     WHERE name LIKE '%memory%'
   "
   ```

#### Resolution
1. **Service Restart**
   ```bash
   # Graceful restart
   docker compose -f docker-compose.pc1.yml restart --timeout 30 janus-api
   
   # Force restart if stuck
   docker kill janus_api && docker start janus_api
   ```

2. **Configuration Tuning**
   ```bash
   # Update memory limits
   export WORKER_MEMORY_LIMIT=2G
   export MAX_WORKERS=4
   
   # Restart with new limits
   docker compose -f docker-compose.pc1.yml up -d
   ```

---

## Infrastructure Incident Response

### Database Failure

#### PostgreSQL Failure
```bash
# Check database status
docker exec postgres pg_isready

# Check logs for errors
docker compose -f docker-compose.pc1.yml logs postgres | tail -100

# Check disk space
docker exec postgres df -h

# Check connection count
docker exec postgres psql -c "SELECT count(*) FROM pg_stat_activity;"
```

#### Recovery Procedures
1. **Minor Issues**
   ```bash
   # Restart PostgreSQL
   docker compose -f docker-compose.pc1.yml restart postgres
   
   # Check for corruption
   docker exec postgres psql -c "
     SELECT 
       schemaname,
       tablename,
       n_tup_ins + n_tup_upd + n_tup_del as total_changes
     FROM pg_stat_user_tables
   "
   ```

2. **Major Issues**
   ```bash
   # Restore from backup
   docker stop postgres
   docker rm postgres
   
   # Restore data volume
   docker run --rm \
     -v janus_postgres_data:/data \
     -v $(pwd)/backups:/backup \
     postgres:13 \
     tar -xzf /backup/postgres_$(date +%Y%m%d).tar.gz -C /data
   
   # Restart service
   docker compose -f docker-compose.pc1.yml up -d postgres
   ```

### Redis Failure

#### Detection and Recovery
```bash
# Check Redis status
docker exec redis redis-cli ping

# Check memory usage
docker exec redis redis-cli info memory

# Check for keys
docker exec redis redis-cli dbsize
```

#### Recovery Actions
```bash
# Restart Redis
docker compose -f docker-compose.pc1.yml restart redis

# Clear corrupted data
docker exec redis redis-cli FLUSHALL

# Restore from backup if needed
docker exec redis redis-cli --rdb /tmp/dump.rdb
```

### Network Issues

#### Diagnosis
```bash
# Check network connectivity
ping -c 4 google.com

# Check Docker networks
docker network ls
docker network inspect bridge

# Check port availability
netstat -tuln | grep :8000

# Check firewall rules
iptables -L -n
```

#### Resolution
```bash
# Restart Docker networking
sudo systemctl restart docker

# Recreate networks
docker network prune
docker compose -f docker-compose.pc1.yml up -d

# Check service discovery
docker exec janus_api nslookup postgres
```

---

## Data Recovery Procedures

### Backup Verification

#### Automated Backup Check
```bash
# List available backups
ls -la backups/

# Verify backup integrity
for backup in backups/*.tar.gz; do
  echo "Checking $backup..."
  tar -tzf "$backup" > /dev/null && echo "✅ Valid" || echo "❌ Corrupted"
done

# Check backup age
find backups/ -name "*.tar.gz" -mtime +7 -exec ls -la {} \;
```

#### Database Backup Verification
```bash
# Test backup restoration (dry run)
docker run --rm \
  -v $(pwd)/backups:/backups \
  postgres:13 \
  pg_restore --list /backups/postgres_latest.dump

# Check backup size trends
python scripts/analyze_backup_trends.py --days 30
```

### Point-in-Time Recovery

#### Database PITR
```bash
# Stop current database
docker compose -f docker-compose.pc1.yml stop postgres

# Restore to specific time
docker run --rm \
  -v janus_postgres_data:/var/lib/postgresql/data \
  -v $(pwd)/backups:/backup \
  postgres:13 \
  pg_restore -v -d janus /backup/postgres_$(date +%Y%m%d_%H%M).dump

# Verify restoration
docker compose -f docker-compose.pc1.yml up -d postgres
docker exec postgres pg_isready
```

#### File System Recovery
```bash
# Restore application data
docker run --rm \
  -v janus_app_data:/data \
  -v $(pwd)/backups:/backup \
  alpine:latest \
  tar -xzf /backup/app_data_$(date +%Y%m%d).tar.gz -C /data

# Restore user uploads
docker run --rm \
  -v janus_uploads:/uploads \
  -v $(pwd)/backups:/backup \
  alpine:latest \
  tar -xzf /backup/uploads_$(date +%Y%m%d).tar.gz -C /uploads
```

---

## Post-Incident Review

### Timeline Documentation

#### Required Information
1. **Detection Time**: When was the issue first noticed?
2. **Response Time**: When did response team assemble?
3. **Investigation Time**: When was root cause identified?
4. **Resolution Time**: When was service fully restored?
5. **Communication Timeline**: All stakeholder notifications

#### Data Collection
```bash
# Export incident logs
docker compose -f docker-compose.pc1.yml logs \
  --since "2024-01-01T00:00:00" \
  --until "2024-01-01T23:59:59" \
  > incident_logs_$(date +%Y%m%d).log

# Export metrics data
curl "http://localhost:8000/api/v1/observability/metrics/summary" \
  > incident_metrics_$(date +%Y%m%d).json

# Generate timeline report
python scripts/generate_incident_timeline.py \
  --start-time "2024-01-01T00:00:00" \
  --end-time "2024-01-01T23:59:59" \
  --output incident_timeline_$(date +%Y%m%d).md
```

### Root Cause Analysis

#### 5-Why Analysis Template
```
Problem: [What happened]

Why 1: [Direct cause]
Why 2: [Underlying cause]
Why 3: [Systemic cause]
Why 4: [Process failure]
Why 5: [Root cause]

Root Cause: [Final answer]
Contributing Factors: [List all]
```

#### Technical Analysis
```bash
# Analyze error patterns
grep -i "error\|failed\|exception" incident_logs_*.log | \
  awk '{print $1, $2, $5}' | \
  sort | uniq -c | sort -nr

# Check deployment correlation
git log --oneline --since="48 hours before incident" --until="incident start"

# Analyze performance metrics
python scripts/analyze_performance_during_incident.py \
  --metrics-file incident_metrics_$(date +%Y%m%d).json
```

### Action Items

#### Immediate Actions (0-7 days)
- [ ] Fix identified vulnerabilities
- [ ] Update monitoring rules
- [ ] Review and update procedures
- [ ] Conduct team training

#### Short-term Actions (1-4 weeks)
- [ ] Implement preventive measures
- [ ] Update documentation
- [ ] Improve monitoring coverage
- [ ] Conduct security audit (if applicable)

#### Long-term Actions (1-6 months)
- [ ] Architecture improvements
- [ ] Tool upgrades
- [ ] Process optimizations
- [ ] Team capability building

---

## Emergency Contacts

### Internal Contacts

#### Executive Team
- **CEO**: ceo@company.com, +1-XXX-XXX-XXXX
- **CTO**: cto@company.com, +1-XXX-XXX-XXXX
- **VP Engineering**: vp-eng@company.com, +1-XXX-XXX-XXXX

#### Engineering Team
- **Engineering Manager**: eng-manager@company.com
- **Tech Lead**: tech-lead@company.com
- **DevOps Lead**: devops-lead@company.com
- **Security Lead**: security-lead@company.com

#### Support Team
- **Customer Support**: support@janus-ai.com
- **Customer Success**: success@janus-ai.com
- **Sales Team**: sales@janus-ai.com

### External Contacts

#### Vendors
- **Cloud Provider**: support@cloudprovider.com
- **CDN Provider**: support@cdnprovider.com
- **Monitoring Service**: support@monitoring.com

#### Regulatory
- **Data Protection Authority**: dpa@region.gov
- **Cybersecurity Agency**: cybersecurity@gov.agency

#### Legal
- **Legal Counsel**: legal@lawfirm.com
- **Compliance Officer**: compliance@company.com

---

## Quick Reference Commands

### Health Checks
```bash
# System health
curl -sf http://localhost:8000/health
curl -sf http://localhost:8000/healthz

# Service health
curl -sf http://localhost:8000/api/v1/system/status
curl -sf http://localhost:8000/api/v1/system/health/services

# Worker status
curl -sf http://localhost:8000/api/v1/workers/status
```

### Log Analysis
```bash
# Recent errors
docker compose -f docker-compose.pc1.yml logs --tail=100 | grep -i error

# Specific service logs
docker compose -f docker-compose.pc1.yml logs [service-name] --tail=200

# Search logs by time
docker compose -f docker-compose.pc1.yml logs \
  --since "2024-01-01T12:00:00" \
  --until "2024-01-01T13:00:00"
```

### System Recovery
```bash
# Restart all services
docker compose -f docker-compose.pc1.yml restart
docker compose -f docker-compose.pc2.yml restart

# Reset to clean state
docker compose -f docker-compose.pc1.yml down
docker compose -f docker-compose.pc2.yml down
docker system prune -a
```

### Evidence Collection
```bash
# Create evidence package
mkdir -p evidence/$(date +%Y%m%d_%H%M%S)

# Collect logs
docker compose -f docker-compose.pc1.yml logs > evidence/logs_pc1.txt
docker compose -f docker-compose.pc2.yml logs > evidence/logs_pc2.txt

# Collect metrics
curl -sf http://localhost:8000/api/v1/observability/metrics/summary > evidence/metrics.json

# Package evidence
tar -czf evidence_$(date +%Y%m%d_%H%M%S).tar.gz evidence/
```

---

*This runbook is maintained by the Janus Operations Team. Last updated: [DATE]*

*For questions or updates, contact: operations@janus-ai.com*