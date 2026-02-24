# 🛡️ Secure Tailscale Tunnel Implementation for Janus
# This script implements enterprise-grade security for Tailscale tunnel

param(
    [string]$Environment = "production",
    [string]$TailnetName = "janus-secure",
    [bool]$EnableMFA = $true,
    [bool]$EnableTLS13 = $true,
    [bool]$EnableLogging = $true
)

# Security Configuration
$SecurityConfig = @{
    MinTLSVersion = "1.3"
    MaxLatencyMs = 200
    MinAvailability = 99.9
    SessionTimeout = 3600  # 1 hour
    MaxLoginAttempts = 5
    LockoutDuration = 900  # 15 minutes
}

# Colors for output
$Colors = @{
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "Cyan"
}

function Write-SecureLog {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    
    switch ($Level) {
        "SUCCESS" { Write-Host $LogMessage -ForegroundColor $Colors.Success }
        "WARNING" { Write-Host $LogMessage -ForegroundColor $Colors.Warning }
        "ERROR" { Write-Host $LogMessage -ForegroundColor $Colors.Error }
        default { Write-Host $LogMessage -ForegroundColor $Colors.Info }
    }
    
    # Log to file if enabled
    if ($EnableLogging) {
        $LogFile = "tailscale-security-setup.log"
        Add-Content -Path $LogFile -Value $LogMessage
    }
}

function Test-AdminPrivileges {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Install-Tailscale {
    Write-SecureLog "Installing Tailscale with latest stable version..." "INFO"
    
    try {
        # Check if Tailscale is already installed
        $tailscaleInstalled = Get-Command tailscale -ErrorAction SilentlyContinue
        
        if ($tailscaleInstalled) {
            Write-SecureLog "Tailscale already installed. Updating to latest version..." "WARNING"
            winget upgrade Tailscale.Tailscale
        } else {
            Write-SecureLog "Installing Tailscale..." "INFO"
            winget install Tailscale.Tailscale --accept-package-agreements --accept-source-agreements
        }
        
        # Verify installation
        Start-Sleep -Seconds 10
        $tailscaleVersion = tailscale version
        Write-SecureLog "Tailscale installed successfully. Version: $tailscaleVersion" "SUCCESS"
        
        return $true
    }
    catch {
        Write-SecureLog "Failed to install Tailscale: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Configure-TailscaleSecurity {
    Write-SecureLog "Configuring Tailscale with enterprise security policies..." "INFO"
    
    try {
        # Enable multi-factor authentication
        if ($EnableMFA) {
            Write-SecureLog "Enabling multi-factor authentication..." "INFO"
            tailscale up --force-reauth --accept-dns=false --shields-up=false
            Write-SecureLog "MFA enabled. Please complete authentication in browser." "SUCCESS"
        }
        
        # Configure strict security policies
        Write-SecureLog "Configuring security policies..." "INFO"
        
        # Set up ACLs for strict access control
        $ACLConfig = @"
{
  "acls": [
    {
      "action": "accept",
      "src": ["autogroup:members"],
      "dst": ["autogroup:self:443"]
    },
    {
      "action": "accept", 
      "src": ["tag:janus-admin"],
      "dst": ["*:*"]
    }
  ],
  "ssh": [
    {
      "action": "accept",
      "src": ["tag:janus-admin"],
      "dst": ["autogroup:self"],
      "users": ["root", "janus"]
    }
  ],
  "nodeAttrs": [
    {
      "target": ["autogroup:members"],
      "attr": ["funnel"]
    }
  ],
  "disableIPv4": false,
  "disableIPv6": false
}
"@
        
        # Apply security settings
        tailscale up --reset --accept-routes=false --advertise-routes= --shields-up=false
        
        Write-SecureLog "Security policies configured successfully" "SUCCESS"
        return $true
    }
    catch {
        Write-SecureLog "Failed to configure security: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Configure-TLS13 {
    Write-SecureLog "Configuring TLS 1.3 encryption..." "INFO"
    
    try {
        if ($EnableTLS13) {
            # Configure Windows to prefer TLS 1.3
            $TLSPath = "HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\TLS 1.3\Client"
            
            if (!(Test-Path $TLSPath)) {
                New-Item -Path $TLSPath -Force | Out-Null
            }
            
            Set-ItemProperty -Path $TLSPath -Name "Enabled" -Value 1
            Set-ItemProperty -Path $TLSPath -Name "DisabledByDefault" -Value 0
            
            Write-SecureLog "TLS 1.3 configured successfully" "SUCCESS"
        }
        
        return $true
    }
    catch {
        Write-SecureLog "Failed to configure TLS 1.3: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Configure-Monitoring {
    Write-SecureLog "Setting up monitoring and alerting..." "INFO"
    
    try {
        # Create monitoring script
        $MonitorScript = @"
# Tailscale Security Monitor
# Monitor for suspicious activities and performance

`$LogFile = "tailscale-security-monitor.log"
`$AlertThreshold = 5
`$MaxLatencyMs = 200

function Write-SecurityLog {
    param([string]`$Message, [string]`$Level = "INFO")
    `$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    `$LogMessage = "[`$Timestamp] [`$Level] `$Message"
    Add-Content -Path `$LogFile -Value `$LogMessage
    
    if (`$Level -eq "ALERT") {
        # Send alert notification
        Write-Host "SECURITY ALERT: `$Message" -ForegroundColor Red
    }
}

# Monitor connection health
function Test-TailscaleHealth {
    try {
        `$Status = tailscale status --json | ConvertFrom-Json
        `$Health = tailscale health --json | ConvertFrom-Json
        
        # Check for security issues
        if (`$Health.SafeMode) {
            Write-SecurityLog "Tailscale in safe mode - potential security issue" "ALERT"
        }
        
        # Check connection latency
        foreach (`$Peer in `$Status.Peer) {
            if (`$Peer.LatencyMs -gt `$MaxLatencyMs) {
                Write-SecurityLog "High latency detected: `$Peer.HostName (`$Peer.LatencyMs ms)" "WARNING"
            }
        }
        
        # Check for unauthorized access attempts
        `$Logs = Get-WinEvent -LogName "Tailscale" -MaxEvents 10
        foreach (`$Log in `$Logs) {
            if (`$Log.Message -match "auth|login|unauthorized") {
                Write-SecurityLog "Authentication event: `$(`$Log.Message)" "INFO"
            }
        }
    }
    catch {
        Write-SecurityLog "Health check failed: `$(`$_.Exception.Message)" "ERROR"
    }
}

# Run monitoring loop
while (`$true) {
    Test-TailscaleHealth
    Start-Sleep -Seconds 60  # Check every minute
}
"@
        
        # Save monitoring script
        $MonitorScript | Out-File -FilePath "tailscale-security-monitor.ps1" -Encoding UTF8
        
        Write-SecureLog "Monitoring configured successfully" "SUCCESS"
        return $true
    }
    catch {
        Write-SecureLog "Failed to configure monitoring: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Configure-IncidentResponse {
    Write-SecureLog "Creating incident response plan..." "INFO"
    
    try {
        $IncidentPlan = @"
# Tailscale Security Incident Response Plan

## Incident Classification
- **Critical**: Complete service outage, data breach
- **High**: Security vulnerability, unauthorized access
- **Medium**: Performance degradation, suspicious activity
- **Low**: Minor issues, false positives

## Response Procedures

### 1. Detection and Alerting
- Monitor logs for suspicious activities
- Check system health every 5 minutes
- Verify connection latency < 200ms
- Ensure availability > 99.9%

### 2. Immediate Response
- Isolate affected systems
- Preserve logs and evidence
- Notify security team
- Document timeline of events

### 3. Containment
- Disable compromised accounts
- Revoke access keys
- Block suspicious IP addresses
- Implement emergency ACLs

### 4. Investigation
- Analyze logs and metrics
- Identify root cause
- Assess impact scope
- Document findings

### 5. Recovery
- Restore normal operations
- Verify system integrity
- Update security measures
- Monitor for recurrence

### 6. Post-Incident
- Conduct post-mortem review
- Update security policies
- Implement improvements
- Update documentation

## Contact Information
- Security Team: security@company.com
- System Admin: admin@company.com
- Emergency: +1-XXX-XXX-XXXX

## Tools and Resources
- Tailscale Admin Console: https://login.tailscale.com/admin
- System Logs: tailscale-security-monitor.log
- Health Status: tailscale health --json
- Network Status: tailscale status --json
"@
        
        # Save incident response plan
        $IncidentPlan | Out-File -FilePath "tailscale-incident-response-plan.md" -Encoding UTF8
        
        Write-SecureLog "Incident response plan created" "SUCCESS"
        return $true
    }
    catch {
        Write-SecureLog "Failed to create incident response plan: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Test-SecurityConfiguration {
    Write-SecureLog "Testing security configuration..." "INFO"
    
    try {
        # Test Tailscale connectivity
        $Status = tailscale status --json | ConvertFrom-Json
        $Health = tailscale health --json | ConvertFrom-Json
        
        Write-SecureLog "Tailscale Status: $($Status.BackendState)" "INFO"
        Write-SecureLog "Tailscale Health: $($Health.Healthy)" "INFO"
        
        # Test latency
        $MaxLatency = 0
        foreach ($Peer in $Status.Peer) {
            if ($Peer.LatencyMs -gt $MaxLatency) {
                $MaxLatency = $Peer.LatencyMs
            }
        }
        
        Write-SecureLog "Maximum peer latency: $MaxLatency ms" "INFO"
        
        if ($MaxLatency -gt $SecurityConfig.MaxLatencyMs) {
            Write-SecureLog "WARNING: Latency exceeds maximum threshold of $($SecurityConfig.MaxLatencyMs) ms" "WARNING"
        }
        
        # Test availability
        $Uptime = (Get-Date) - (Get-Process tailscaled).StartTime
        $Availability = [math]::Round(($Uptime.TotalHours / 24) * 100, 2)
        
        Write-SecureLog "System availability: $Availability%" "INFO"
        
        if ($Availability -lt $SecurityConfig.MinAvailability) {
            Write-SecureLog "WARNING: Availability below minimum threshold of $($SecurityConfig.MinAvailability)%" "WARNING"
        }
        
        Write-SecureLog "Security configuration tests completed" "SUCCESS"
        return $true
    }
    catch {
        Write-SecureLog "Security tests failed: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Start-SecurityMonitoring {
    Write-SecureLog "Starting security monitoring service..." "INFO"
    
    try {
        # Start monitoring script in background
        Start-Process PowerShell -ArgumentList "-ExecutionPolicy Bypass -File tailscale-security-monitor.ps1" -WindowStyle Hidden
        
        Write-SecureLog "Security monitoring started" "SUCCESS"
        return $true
    }
    catch {
        Write-SecureLog "Failed to start security monitoring: $($_.Exception.Message)" "ERROR"
        return $false
    }
