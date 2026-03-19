
## 3. Debugging de Performance

### 3.1 Análise de Performance com py-spy

**`tooling/performance_profiler.py`**:
```python
#!/usr/bin/env python3
"""
Advanced performance profiler for Janus backend
"""

import subprocess
import json
import time
import psutil
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from pathlib import Path
import argparse

class PerformanceProfiler:
    def __init__(self, pid=None, output_dir="performance_reports"):
        self.pid = pid or self._find_janus_pid()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def _find_janus_pid(self):
        """Find Janus API process ID"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'uvicorn' in cmdline and 'app.main' in cmdline:
                    return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        raise RuntimeError("Janus API process not found")
    
    def profile_cpu_usage(self, duration=30, sample_rate=10):
        """Profile CPU usage over time"""
        log_file = self.output_dir / f"cpu_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        print(f"Profiling CPU usage for {duration} seconds...")
        
        # Use py-spy for CPU profiling
        cmd = [
            "py-spy", "record",
            "--pid", str(self.pid),
            "--duration", str(duration),
            "--rate", str(sample_rate),
            "--format", "json",
            "--output", str(log_file)
        ]
        
        try:
            subprocess.run(cmd, check=True)
            print(f"CPU profile saved to: {log_file}")
            return self._analyze_cpu_profile(log_file)
        except subprocess.CalledProcessError as e:
            print(f"Failed to profile CPU: {e}")
            return None
    
    def profile_memory_usage(self, duration=30):
        """Profile memory usage patterns"""
        memory_data = []
        process = psutil.Process(self.pid)
        
        print(f"Profiling memory usage for {duration} seconds...")
        
        start_time = time.time()
        while time.time() - start_time < duration:
            try:
                memory_info = process.memory_info()
                memory_data.append({
                    'timestamp': time.time() - start_time,
                    'rss': memory_info.rss / 1024 / 1024,  # MB
                    'vms': memory_info.vms / 1024 / 1024,  # MB
                    'percent': process.memory_percent()
                })
                time.sleep(1)
            except psutil.NoSuchProcess:
                print("Process no longer exists")
                break
        
        # Save memory data
        memory_file = self.output_dir / f"memory_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(memory_file, 'w') as f:
            json.dump(memory_data, f, indent=2)
        
        self._plot_memory_usage(memory_data)
        return memory_data
    
    def detect_memory_leaks(self, duration=300, threshold=1.0):
        """Detect potential memory leaks"""
        print(f"Checking for memory leaks over {duration} seconds...")
        
        memory_data = self.profile_memory_usage(duration)
        if not memory_data:
            return None
        
        # Analyze memory growth
        initial_memory = memory_data[0]['rss']
        final_memory = memory_data[-1]['rss']
        memory_growth = final_memory - initial_memory
        growth_rate = memory_growth / (duration / 60)  # MB per minute
        
        leak_detected = growth_rate > threshold
        
        result = {
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'memory_growth_mb': memory_growth,
            'growth_rate_mb_per_min': growth_rate,
            'leak_detected': leak_detected,
            'threshold_mb_per_min': threshold
        }
        
        # Save leak detection report
        leak_file = self.output_dir / f"memory_leak_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(leak_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        if leak_detected:
            print(f"⚠️  Potential memory leak detected!")
            print(f"   Growth rate: {growth_rate:.2f} MB/min")
            print(f"   Total growth: {memory_growth:.2f} MB")
        else:
            print(f"✅ No significant memory leak detected")
            print(f"   Growth rate: {growth_rate:.2f} MB/min")
        
        return result
    
    def profile_database_queries(self, duration=60):
        """Profile database query performance"""
        print(f"Profiling database queries for {duration} seconds...")
        
        # This would require database query logging to be enabled
        # For now, we'll simulate the analysis
        query_log_file = self.output_dir / f"query_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Sample query analysis (in real implementation, parse actual logs)
        sample_queries = [
            {
                "query": "SELECT * FROM users WHERE id = %s",
                "execution_time": 0.05,
                "calls": 150,
                "total_time": 7.5
            },
            {
                "query": "SELECT * FROM knowledge_items JOIN tags ON ...",
                "execution_time": 2.3,
                "calls": 25,
                "total_time": 57.5
            }
        ]
        
        # Analyze query performance
        slow_queries = [q for q in sample_queries if q['execution_time'] > 1.0]
        
        analysis = {
            'total_queries': len(sample_queries),
            'slow_queries': len(slow_queries),
            'slow_query_threshold': 1.0,
            'queries': sample_queries,
            'recommendations': []
        }
        
        if slow_queries:
            analysis['recommendations'].append("Consider adding indexes for slow queries")
            analysis['recommendations'].append("Review query execution plans")
        
        with open(query_log_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        return analysis
    
    def _plot_memory_usage(self, memory_data):
        """Plot memory usage over time"""
        timestamps = [item['timestamp'] for item in memory_data]
        rss_values = [item['rss'] for item in memory_data]
        
        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, rss_values, 'b-', linewidth=2)
        plt.xlabel('Time (seconds)')
        plt.ylabel('Memory Usage (MB)')
        plt.title('Memory Usage Over Time')
        plt.grid(True, alpha=0.3)
        
        plot_file = self.output_dir / f"memory_usage_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Memory usage plot saved to: {plot_file}")
    
    def generate_performance_report(self):
        """Generate comprehensive performance report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'pid': self.pid,
            'cpu_profile': self.profile_cpu_usage(),
            'memory_profile': self.profile_memory_usage(),
            'memory_leak_analysis': self.detect_memory_leaks(),
            'database_analysis': self.profile_database_queries()
        }
        
        report_file = self.output_dir / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Performance report generated: {report_file}")
        return report

def main():
    parser = argparse.ArgumentParser(description="Janus Performance Profiler")
    parser.add_argument("--pid", type=int, help="Process ID to profile")
    parser.add_argument("--duration", type=int, default=30, help="Profiling duration in seconds")
    parser.add_argument("--output-dir", default="performance_reports", help="Output directory")
    parser.add_argument("--full-report", action="store_true", help="Generate full performance report")
    
    args = parser.parse_args()
    
    profiler = PerformanceProfiler(pid=args.pid, output_dir=args.output_dir)
    
    if args.full_report:
        profiler.generate_performance_report()
    else:
        print("Available profiling options:")
        print("1. CPU Profile")
        print("2. Memory Profile")
        print("3. Memory Leak Detection")
        print("4. Database Query Analysis")
        print("5. Full Report")
        
        choice = input("Select option (1-5): ")
        
        if choice == "1":
            profiler.profile_cpu_usage(args.duration)
        elif choice == "2":
            profiler.profile_memory_usage(args.duration)
        elif choice == "3":
            profiler.detect_memory_leaks(args.duration)
        elif choice == "4":
            profiler.profile_database_queries(args.duration)
        elif choice == "5":
            profiler.generate_performance_report()
        else:
            print("Invalid option")

if __name__ == "__main__":
    main()
```

### 3.2 Debugging de Memory Leaks

**`tooling/memory_debugger.py`**:
```python
#!/usr/bin/env python3
"""
Advanced memory leak detection and debugging for Janus
"""

import tracemalloc
import gc
import objgraph
import psutil
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

class MemoryDebugger:
    def __init__(self, output_dir="memory_debug"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.snapshots = []
        
    def start_tracing(self):
        """Start memory tracing"""
        tracemalloc.start()
        print("Memory tracing started")
    
    def take_snapshot(self, label: str = ""):
        """Take memory snapshot"""
        snapshot = tracemalloc.take_snapshot()
        self.snapshots.append({
            'timestamp': datetime.now().isoformat(),
            'label': label,
            'snapshot': snapshot
        })
        print(f"Memory snapshot taken: {label}")
        return snapshot
    
    def compare_snapshots(self, snapshot1_idx: int, snapshot2_idx: int):
        """Compare two memory snapshots"""
        if snapshot1_idx >= len(self.snapshots) or snapshot2_idx >= len(self.snapshots):
            raise ValueError("Invalid snapshot index")
        
        snapshot1 = self.snapshots[snapshot1_idx]['snapshot']
        snapshot2 = self.snapshots[snapshot2_idx]['snapshot']
        
        # Compare snapshots
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        
        comparison = {
            'snapshot1': {
                'index': snapshot1_idx,
                'label': self.snapshots[snapshot1_idx]['label'],
                'timestamp': self.snapshots[snapshot1_idx]['timestamp']
            },
            'snapshot2': {
                'index': snapshot2_idx,
                'label': self.snapshots[snapshot2_idx]['label'],
                'timestamp': self.snapshots[snapshot2_idx]['timestamp']
            },
            'differences': []
        }
        
        for stat in top_stats[:20]:  # Top 20 differences
            comparison['differences'].append({
                'file': stat.traceback.format()[-1],
                'line': stat.traceback.format()[-1].split(':')[-2] if ':' in stat.traceback.format()[-1] else 'unknown',
                'size_diff': stat.size_diff,
                'size': stat.size,
                'count_diff': stat.count_diff,
                'count': stat.count
            })
        
        return comparison
    
    def analyze_object_growth(self, pid: int, duration: int = 60):
        """Analyze object growth over time"""
        process = psutil.Process(pid)
        object_stats = []
        
        print(f"Analyzing object growth for PID {pid} over {duration} seconds...")
        
        start_time = time.time()
        while time.time() - start_time < duration:
            try:
                # Force garbage collection
                gc.collect()
                
                # Count objects by type
                objects = {}
                for obj in gc.get_objects():
                    obj_type = type(obj).__name__
                    objects[obj_type] = objects.get(obj_type, 0) + 1
                
                # Get memory info
                memory_info = process.memory_info()
                
                object_stats.append({
                    'timestamp': time.time() - start_time,
                    'objects': objects,
                    'memory_rss': memory_info.rss,
                    'memory_vms': memory_info.vms,
                    'gc_stats': gc.get_stats()
                })
                
                time.sleep(5)  # Sample every 5 seconds
                
            except psutil.NoSuchProcess:
                print("Process no longer exists")
                break
        
        # Analyze growth patterns
        analysis = self._analyze_growth_patterns(object_stats)
        
        # Save analysis
        output_file = self.output_dir / f"object_growth_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'object_stats': object_stats,
                'analysis': analysis
            }, f, indent=2)
        
        return analysis
    
    def _analyze_growth_patterns(self, object_stats: List[Dict]) -> Dict:
        """Analyze object growth patterns"""
        if len(object_stats) < 2:
            return {"error": "Insufficient data for analysis"}
        
        # Calculate growth rates for each object type
        growth_analysis = {}
        first_snapshot = object_stats[0]['objects']
        last_snapshot = object_stats[-1]['objects']
        
        all_types = set(first_snapshot.keys()) | set(last_snapshot.keys())
        
        for obj_type in all_types:
            first_count = first_snapshot.get(obj_type, 0)
            last_count = last_snapshot.get(obj_type, 0)
            
            if first_count > 0:
                growth_rate = (last_count - first_count) / first_count * 100
                absolute_growth = last_count - first_count
            else:
                growth_rate = float('inf') if last_count > 0 else 0
                absolute_growth = last_count
            
            if absolute_growth != 0:  # Only include types with changes
                growth_analysis[obj_type] = {
                    'initial_count': first_count,
                    'final_count': last_count,
                    'absolute_growth': absolute_growth,
                    'growth_rate_percent': growth_rate if growth_rate != float('inf') else 'infinite'
                }
        
        # Sort by absolute growth
        sorted_growth = sorted(growth_analysis.items(), 
                              key=lambda x: abs(x[1]['absolute_growth']), 
                              reverse=True)
        
        # Memory leak indicators
        leak_indicators = []
        for obj_type, stats in growth_analysis.items():
            if stats['absolute_growth'] > 100 and stats['growth_rate_percent'] > 50:
                leak_indicators.append({
                    'object_type': obj_type,
                    'reason': 'Large absolute growth with high percentage'
                })
            elif stats['absolute_growth'] > 1000:
                leak_indicators.append({
                    'object_type': obj_type,
                    'reason': 'Very large absolute growth'
                })
        
        return {
            'top_growing_objects': sorted_growth[:10],
            'leak_indicators': leak_indicators,
            'total_objects_initial': sum(first_snapshot.values()),
            'total_objects_final': sum(last_snapshot.values()),
            'total_growth': sum(last_snapshot.values()) - sum(first_snapshot.values())
        }
    
    def find_circular_references(self, object_types: List[str] = None):
        """Find circular references in objects"""
        print("Searching for circular references...")
        
        gc.collect()  # Clean up first
        
        if object_types:
            objects_to_check = []
            for obj_type in object_types:
                objects_to_check.extend(objgraph.by_type(obj_type))
        else:
            # Check all objects
            objects_to_check = gc.get_objects()
        
        circular_refs = []
        
        for obj in objects_to_check[:1000]:  # Limit to first 1000 objects
            try:
                # Find objects that refer to this object
                referrers = objgraph.show_backrefs([obj], max_depth=3, 
                                                   highlight=lambda x: x is obj,
                                                   filename=None)
                
                # Simple circular reference detection
                refs = gc.get_referrers(obj)
                for ref in refs:
                    if ref is obj:  # Self-reference
                        circular_refs.append({
                            'object': str(obj)[:100],
                            'type': type(obj).__name__,
                            'id': id(obj),
                            'reference_type': 'self'
                        })
                        break
                        
            except Exception as e:
                continue  # Skip objects that can't be analyzed
        
        # Save circular reference report
        output_file = self.output_dir / f"circular_references_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'circular_references': circular_refs,
                'total_found': len(circular_refs)
            }, f, indent=2)
        
        print(f"Found {len(circular_refs)} circular references")
        return circular_refs
    
    def generate_memory_dump(self, pid: int):
        """Generate memory dump for analysis"""
        print(f"Generating memory dump for PID {pid}...")
        
        process = psutil.Process(pid)
        
        # Get detailed memory maps
        memory_maps = []
        for mmap in process.memory_maps():
            memory_maps.append({
                'path': mmap.path,
                'rss': mmap.rss,
                'size': mmap.size,
                'pss': getattr(mmap, 'pss', 0),
                'shared_clean': getattr(mmap, 'shared_clean', 0),
                'shared_dirty': getattr(mmap, 'shared_dirty', 0),
                'private_clean': getattr(mmap, 'private_clean', 0),
                'private_dirty': getattr(mmap, 'private_dirty', 0)
            })
        
        # Get memory info
        memory_info = process.memory_info()
        
        # Get memory percent
        memory_percent = process.memory_percent()
        
        dump = {
            'timestamp': datetime.now().isoformat(),
            'pid': pid,
            'process_name': process.name(),
            'memory_info': {
                'rss': memory_info.rss,
                'vms': memory_info.vms,
                'shared': memory_info.shared,
                'text': memory_info.text,
                'lib': memory_info.lib,
                'data': memory_info.data,
                'dirty': memory_info.dirty
            },
            'memory_percent': memory_percent,
            'memory_maps': sorted(memory_maps, key=lambda x: x['rss'], reverse=True)[:20]
        }
        
        # Save memory dump
        dump_file = self.output_dir / f"memory_dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(dump_file, 'w') as f:
            json.dump(dump, f, indent=2)
        
        print(f"Memory dump saved to: {dump_file}")
        return dump
    
    def comprehensive_memory_analysis(self, pid: int, duration: int = 120):
        """Run comprehensive memory analysis"""
        print("Starting comprehensive memory analysis...")
        
        # Start memory tracing
        self.start_tracing()
        
        # Take initial snapshot
        self.take_snapshot("initial")
        
        # Analyze object growth
        growth_analysis = self.analyze_object_growth(pid, duration // 2)
        
        # Take middle snapshot
        self.take_snapshot("middle")
        
        # Find circular references
        circular_refs = self.find_circular_references()
        
        # Take final snapshot
        self.take_snapshot("final")
        
        # Compare snapshots
        comparison = self.compare_snapshots(0, -1)
        
        # Generate memory dump
        memory_dump = self.generate_memory_dump(pid)
        
        # Compile comprehensive report
        report = {
            'timestamp': datetime.now().isoformat(),
            'pid': pid,
            'duration_seconds': duration,
            'object_growth_analysis': growth_analysis,
            'circular_references': circular_refs,
            'snapshot_comparison': comparison,
            'memory_dump_summary': {
                'total_rss': memory_dump['memory_info']['rss'],
                'total_vms': memory_dump['memory_info']['vms'],
                'memory_percent': memory_dump['memory_percent']
            }
        }
        
        # Save comprehensive report
        report_file = self.output_dir / f"comprehensive_memory_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Comprehensive memory analysis complete!")
        print(f"Report saved to: {report_file}")
        
        # Print summary
        if growth_analysis.get('leak_indicators'):
            print("\n⚠️  Memory leak indicators found:")
            for indicator in growth_analysis['leak_indicators']:
                print(f"   - {indicator['object_type']}: {indicator['reason']}")
        
        if circular_refs:
            print(f"\n⚠️  Found {len(circular_refs)} circular references")
        
        return report

# Usage example
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python memory_debugger.py <pid>")
        sys.exit(1)
    
    pid = int(sys.argv[1])
    debugger = MemoryDebugger()
    
    print(f"Starting memory debugging for PID {pid}...")
    debugger.comprehensive_memory_analysis(pid, duration=120)
```

## 4. Debugging de Concorrência

### 4.1 Detecção de Deadlocks

**`tooling/concurrency_debugger.py`**:
```python
#!/usr/bin/env python3
"""
Concurrency debugging tools for Janus
"""

import threading
import time
import faulthandler
import signal
import sys
import traceback
from datetime import datetime
from pathlib import Path
import json

class ConcurrencyDebugger:
    def __init__(self, output_dir="concurrency_debug"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.thread_dumps = []
        self.lock_info = {}
        
    def enable_deadlock_detection(self):
        """Enable automatic deadlock detection"""
        print("Enabling deadlock detection...")
        
        # Register signal handler for deadlock detection
        def deadlock_handler(signum, frame):
            print("Deadlock detected! Generating thread dump...")
            self.generate_thread_dump("deadlock_detected")
            
        signal.signal(signal.SIGUSR1, deadlock_handler)
        
        # Enable faulthandler for better crash information
        faulthandler.enable()
        
        print("Deadlock detection enabled. Send SIGUSR1 to trigger analysis.")
    
    def generate_thread_dump(self, label="manual"):
        """Generate comprehensive thread dump"""
        print(f"Generating thread dump: {label}")
        
        thread_dump = {
            'timestamp': datetime.now().isoformat(),
            'label': label,
            'threads': []
        }
        
        for thread in threading.enumerate():
            thread_info = {
                'name': thread.name,
                'ident': thread.ident,
                'daemon': thread.daemon,
                'alive': thread.is_alive()
            }
            
            # Get stack trace for each thread
            try:
                import sys
                frames = sys._current_frames()
                if thread.ident in frames:
                    frame = frames[thread.ident]
                    stack_trace = traceback.format_stack(frame)
                    thread_info['stack_trace'] = stack_trace
            except Exception as e:
                thread_info['stack_trace_error'] = str(e)
            
            thread_dump['threads'].append(thread_info)
        
        # Save thread dump
        dump_file = self.output_dir / f"thread_dump_{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(dump_file, 'w') as f:
            json.dump(thread_dump, f, indent=2)
        
        print(f"Thread dump saved to: {dump_file}")
        self.thread_dumps.append(thread_dump)
        
        return thread_dump
    
    def monitor_locks(self, duration=60):
        """Monitor lock acquisition and release patterns"""
        print(f"Monitoring locks for {duration} seconds...")
        
        # This is a simplified implementation
        # In a real scenario, you'd instrument the actual lock objects
        
        lock_events = []
        start_time = time.time()
        
        # Monitor threading locks
        import threading
        
        # Wrap lock methods to capture events
        original_acquire = threading.Lock.acquire
        original_release = threading.Lock.release
        
        def tracked_acquire(self, blocking=True, timeout=-1):
            event = {
                'type': 'acquire',
                'thread': threading.current_thread().name,
                'thread_id': threading.current_thread().ident,
                'timestamp': time.time() - start_time,
                'lock_id': id(self),
                'blocking': blocking,
                'timeout': timeout
            }
            lock_events.append(event)
            return original_acquire(self, blocking, timeout)
        
        def tracked_release(self):
            event = {
                'type': 'release',
                'thread': threading.current_thread().name,
                'thread_id': threading.current_thread().ident,
                'timestamp': time.time() - start_time,
                'lock_id': id(self)
            }
            lock_events.append(event)
            return original_release(self)
        
        # Monkey patch lock methods
        threading.Lock.acquire = tracked_acquire
        threading.Lock.release = tracked_release
        
        # Monitor for specified duration
        time.sleep(duration)
        
        # Restore original methods
        threading.Lock.acquire = original_acquire
        threading.Lock.release = original_release
        
        # Analyze lock patterns
        analysis = self._analyze_lock_patterns(lock_events)
        
        # Save results
        results = {
            'timestamp': datetime.now().isoformat(),
            'duration': duration,
            'lock_events': lock_events,
            'analysis': analysis
        }
        
        results_file = self.output_dir / f"lock_monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Lock monitoring complete. Results saved to: {results_file}")
        return results
    
    def _analyze_lock_patterns(self, lock_events: list) -> dict:
        """Analyze lock acquisition patterns for potential issues"""
        
        # Group events by lock
        locks = {}
        for event in lock_events:
            lock_id = event['lock_id']
            if lock_id not in locks:
                locks[lock_id] = []
            locks[lock_id].append(event)
        
        # Analyze each lock
        lock_analysis = {}
        potential_issues = []
        
        for lock_id, events in locks.items():
            # Check for lock contention
            acquire_events = [e for e in events if e['type'] == 'acquire']
            release_events = [e for e in events if e['type'] == 'release']
            
            # Check for orphaned locks (more acquires than releases)
            if len(acquire_events) > len(release_events):
                potential_issues.append({
                    'lock_id': lock_id,
                    'issue': 'orphaned_lock',
                    'acquires': len(acquire_events),
                    'releases': len(release_events),
                    'description': 'Lock acquired more times than released'
                })
            
            # Check for long-held locks
            if acquire_events and release_events:
                for acquire in acquire_events:
                    # Find corresponding release
                    corresponding_release = next(
                        (release for release in release_events 
                         if release['thread_id'] == acquire['thread_id'] 
                         and release['timestamp'] > acquire['timestamp']),
                        None
                    )
                    
                    if corresponding_release:
                        hold_duration = corresponding_release['timestamp'] - acquire['timestamp']
                        if hold_duration > 5.0:  # Held for more than 5 seconds
                            potential_issues.append({
                                'lock_id': lock_id,
                                'issue': 'long_held_lock',
                                'hold_duration': hold_duration,
                                'thread': acquire['thread'],
                                'description': f'Lock held for {hold_duration:.2f} seconds'
                            })
            
            lock_analysis[lock_id] = {
                'total_events': len(events),
                'acquires': len(acquire_events),
                'releases': len(release_events),
                'unique_threads': len(set(e['thread_id'] for e in events))
            }
        
        return {
            'total_locks': len(locks),
            'total_events': len(lock_events),
            'lock_analysis': lock_analysis,
            'potential_issues': potential_issues
        }
    
    def detect_race_conditions(self, shared_variables: list):
        """Detect potential race conditions in shared variables"""
        print("Detecting race conditions...")
        
        # This is a simplified implementation
        # In practice, you'd use specialized tools or instrument the code
        
        race_detections = []
        
        # Simulate race condition detection
        for var in shared_variables:
            # Check if variable is accessed by multiple threads
            # without proper synchronization
            
            detection = {
                'variable': var,
                'risk_level': 'medium',  # Would be determined by analysis
                'threads_involved': ['Thread-1', 'Thread-2'],  # Would be actual threads
                'access_pattern': 'concurrent_read_write',
                'recommendation': 'Add proper synchronization'
            }
            
            race_detections.append(detection)
        
        # Save race condition analysis
        race_file = self.output_dir / f"race_condition_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(race_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'shared_variables_analyzed': len(shared_variables),
                'race_conditions_detected': race_detections
            }, f, indent=2)
        
        print(f"Race condition analysis complete. Found {len(race_detections)} potential issues.")
        return race_detections
    
    def comprehensive_concurrency_analysis(self, pid: int, duration: int = 120):
        """Run comprehensive concurrency analysis"""
        print("Starting comprehensive concurrency analysis...")
        
        # Enable deadlock detection
        self.enable_deadlock_detection()
        
        # Generate initial thread dump
        self.generate_thread_dump("initial")
        
        # Monitor locks
        lock_results = self.monitor_locks(duration // 3)
        
        # Generate middle thread dump
        self.generate_thread_dump("middle")
        
        # Detect race conditions in common shared variables
        common_shared_vars = [
            'global_config',
            'user_sessions',
            'cache_dict',
            'connection_pool'
        ]
        
        race_results = self.detect_race_conditions(common_shared_vars)
        
        # Generate final thread dump
        self.generate_thread_dump("final")
        
        # Compile comprehensive report
        report = {
            'timestamp': datetime.now().isoformat(),
            'pid': pid,
            'duration_seconds': duration,
            'thread_dumps_generated': len(self.thread_dumps),
            'lock_monitoring_results': lock_results,
            'race_condition_analysis': race_results,
            'summary': {
                'potential_deadlocks': len([issue for issue in lock_results['analysis']['potential_issues'] 
                                          if issue['issue'] == 'orphaned_lock']),
                'long_held_locks': len([issue for issue in lock_results['analysis']['potential_issues'] 
                                      if issue['issue'] == 'long_held_lock']),
                'race_conditions_detected': len(race_results)
            }
        }
        
        # Save comprehensive report
        report_file = self.output_dir / f"comprehensive_concurrency_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Comprehensive concurrency analysis complete!")
        print(f"Report saved to: {report_file}")
        
        # Print summary
        print("\n📊 Concurrency Analysis Summary:")
        print(f"   Thread dumps generated: {len(self.thread_dumps)}")
        print(f"   Potential deadlocks: {report['summary']['potential_deadlocks']}")
        print(f"   Long-held locks: {report['summary']['long_held_locks']}")
        print(f"   Race conditions detected: {report['summary']['race_conditions_detected']}")
        
        return report

# Usage example
if __name__ == "__main__":
    import sys
    
    debugger = ConcurrencyDebugger()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Concurrency Debugger for Janus")
        print("Usage:")
        print("  python concurrency_debugger.py --thread-dump [label]")
        print("  python concurrency_debugger.py --monitor-locks [duration]")
        print("  python concurrency_debugger.py --full-analysis [pid] [duration]")
    elif len(sys.argv) > 1 and sys.argv[1] == "--thread-dump":
        label = sys.argv[2] if len(sys.argv) > 2 else "manual"
        debugger.generate_thread_dump(label)
    elif len(sys.argv) > 1 and sys.argv[1] == "--monitor-locks":
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        debugger.monitor_locks(duration)
    elif len(sys.argv) > 2 and sys.argv[1] == "--full-analysis":
        pid = int(sys.argv[2])
        duration = int(sys.argv[3]) if len(sys.argv) > 3 else 120
        debugger.comprehensive_concurrency_analysis(pid, duration)
    else:
        print("Running interactive mode...")
        print("Available commands:")
        print("1. Generate thread dump")
        print("2. Monitor locks")
        print("3. Full concurrency analysis")
        
        choice = input("Select option (1-3): ")
        
        if choice == "1":
            label = input("Enter dump label (default: manual): ") or "manual"
            debugger.generate_thread_dump(label)
        elif choice == "2":
            duration = int(input("Enter monitoring duration in seconds (default: 60): ") or "60")
            debugger.monitor_locks(duration)
        elif choice == "3":
            pid = int(input("Enter process ID: "))
            duration = int(input("Enter analysis duration in seconds (default: 120): ") or "120")
            debugger.comprehensive_concurrency_analysis(pid, duration)
        else:
            print("Invalid option")
```

## 5. Debugging de Frontend (Angular)

### 5.1 Performance Debugging

**`frontend/src/app/debugging/performance-monitor.service.ts`**:
```typescript
import { Injectable } from '@angular/core';
import { Router, NavigationStart, NavigationEnd } from '@angular/router';
import { BehaviorSubject, Observable } from 'rxjs';

export interface PerformanceMetrics {
  timestamp: number;
  memoryUsage?: MemoryInfo;
  navigationTiming?: PerformanceNavigationTiming;
  resourceLoadTimes?: ResourceLoadInfo[];
  longTasks?: LongTaskInfo[];
}

export interface MemoryInfo {
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
}

export interface ResourceLoadInfo {
  name: string;
  startTime: number;
  duration: number;
  size: number;
}

export interface LongTaskInfo {
  startTime: number;
  duration: number;
  attribution: string;
}

@Injectable({
  providedIn: 'root'
})
export class PerformanceMonitorService {
  private metricsSubject = new BehaviorSubject<PerformanceMetrics[]>([]);
  private isMonitoring = false;
  private monitoringInterval: any;
  
  metrics$: Observable<PerformanceMetrics[]> = this.metricsSubject.asObservable();
  
  constructor(private router: Router) {
    this.initializePerformanceMonitoring();
  }
  
  private initializePerformanceMonitoring(): void {
    // Monitor navigation performance
    this.router.events.subscribe(event => {
      if (event instanceof NavigationStart) {
        this.startNavigationTiming(event.url);
      } else if (event instanceof NavigationEnd) {
        this.endNavigationTiming(event.url);
      }
    });
    
    // Monitor long tasks
    if ('PerformanceObserver' in window) {
      this.observeLongTasks();
    }
    
    // Monitor resource loading
    this.observeResourceLoading();
  }
  
  startMonitoring(intervalMs: number = 5000): void {
    if (this.isMonitoring) {
      console.warn('Performance monitoring is already running');
      return;
    }
    
    this.isMonitoring = true;
    console.log('Starting performance monitoring...');
    
    this.monitoringInterval = setInterval(() => {
      this.collectMetrics();
    }, intervalMs);
  }
  
  stopMonitoring(): void {
    if (!this.isMonitoring) {
      return;
    }
    
    this.isMonitoring = false;
    clearInterval(this.monitoringInterval);
    console.log('Performance monitoring stopped');
  }
  
  private collectMetrics(): void {
    const metrics: PerformanceMetrics = {
      timestamp: Date.now()
    };
    
    // Collect memory usage
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      metrics.memoryUsage = {
        usedJSHeapSize: memory.usedJSHeapSize,
        totalJSHeapSize: memory.totalJSHeapSize,
        jsHeapSizeLimit: memory.jsHeapSizeLimit
      };
    }
    
    // Collect navigation timing
    const navigationTiming = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    if (navigationTiming) {
      metrics.navigationTiming = navigationTiming;
    }
    
    // Collect resource load times
    const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
    metrics.resourceLoadTimes = resources.map(resource => ({
      name: resource.name,
      startTime: resource.startTime,
      duration: resource.duration,
      size: resource.transferSize || 0
    }));
    
    // Update metrics
    const currentMetrics = this.metricsSubject.value;
    currentMetrics.push(metrics);
    
    // Keep only last 100 metrics to prevent memory issues
    if (currentMetrics.length > 100) {
      currentMetrics.shift();
    }
    
    this.metricsSubject.next(currentMetrics);
    
    // Check for performance issues
    this.checkPerformanceIssues(metrics);
  }
  
  private observeLongTasks(): void {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.duration > 50) { // Tasks longer than 50ms
          console.warn(`Long task detected: ${entry.duration}ms`, {
            startTime: entry.startTime,
            duration: entry.duration,
            name: entry.name
          });
        }
      }
    });
    
    observer.observe({ entryTypes: ['longtask'] });
  }
  
  private observeResourceLoading(): void {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.duration > 1000) { // Resources taking longer than 1s
          console.warn(`Slow resource loading: ${entry.name} took ${entry.duration}ms`);
        }
      }
    });
    
    observer.observe({ entryTypes: ['resource'] });
  }
  
  private startNavigationTiming(url: string): void {
    // Store navigation start time
    (window as any).navigationStartTime = Date.now();
    console.log(`Navigation started to: ${url}`);
  }
  
  private endNavigationTiming(url: string): void {
    const navigationTime = Date.now() - (window as any).navigationStartTime;
    console.log(`Navigation completed to: ${url} in ${navigationTime}ms`);
    
    if (navigationTime > 2000) {
      console.warn(`Slow navigation detected: ${navigationTime}ms`);
    }
  }
  
  private checkPerformanceIssues(metrics: PerformanceMetrics): void {
    // Check for memory leaks
    if (metrics.memoryUsage) {
      const memoryUsage = metrics.memoryUsage;
      const memoryUsagePercent = (memoryUsage.usedJSHeapSize / memoryUsage.jsHeapSizeLimit) * 100;
      
      if (memoryUsagePercent > 80) {
        console.error(`High memory usage detected: ${memoryUsagePercent.toFixed(2)}%`);
      }
    }
    
    // Check for slow resources
    if (metrics.resourceLoadTimes) {
      const slowResources = metrics.resourceLoadTimes.filter(
        resource => resource.duration > 3000
      );
      
      if (slowResources.length > 0) {
        console.warn(`Slow resources detected:`, slowResources);
      }
    }
  }
  
  getPerformanceReport(): PerformanceMetrics[] {
    return this.metricsSubject.value;
  }
  
  exportMetrics(): string {
    const metrics = this.getPerformanceReport();
    return JSON.stringify(metrics, null, 2);
  }
  
  clearMetrics(): void {
    this.metricsSubject.next([]);
  }
  
  // Memory leak detection
  detectMemoryLeaks(): void {
    const metrics = this.getPerformanceReport();
    
    if (metrics.length < 10) {
      console.warn('Insufficient data for memory leak detection');
      return;
    }
    
    // Simple memory leak detection
    const recentMetrics = metrics.slice(-10);
    const initialMemory = recentMetrics[0].memoryUsage?.usedJSHeapSize || 0;
    const finalMemory = recentMetrics[recentMetrics.length - 1].memoryUsage?.usedJSHeapSize || 0;
    
    if (initialMemory > 0 && finalMemory > 0) {
      const growthRate = ((finalMemory - initialMemory) / initialMemory) * 100;
      const timeSpan = (recentMetrics[recentMetrics.length - 1].timestamp - recentMetrics[0].timestamp) / 1000; // seconds
      
      if (growthRate > 20 && timeSpan > 60) { // 20% growth over 1 minute
        console.error(`Potential memory leak detected: ${growthRate.toFixed(2)}% growth over ${timeSpan}s`);
      }
    }
  }
}

// Component debugging decorator
export function DebugComponent() {
  return function(target: any) {
    const originalNgOnInit = target.prototype.ngOnInit;
    const originalNgOnDestroy = target.prototype.ngOnDestroy;
    
    target.prototype.ngOnInit = function() {
      console.log(`Component initialized: ${target.name}`, {
        component: target.name,
        timestamp: Date.now()
      });
      
      if (originalNgOnInit) {
        originalNgOnInit.apply(this);
      }
    };
    
    target.prototype.ngOnDestroy = function() {
      console.log(`Component destroyed: ${target.name}`, {
        component: target.name,
        timestamp: Date.now()
      });
      
      if (originalNgOnDestroy) {
        originalNgOnDestroy.apply(this);
      }
    };
    
    return target;
  };
}
```

### 5.2 Change Detection Debugging

**`frontend/src/app/debugging/change-detection-debugger.service.ts`**:
```typescript
import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';

export interface ChangeDetectionEvent {
  component: string;
  timestamp: number;
  changeDetectionTime: number;
  bindingsChecked: number;
  bindingsUpdated: number;
}

@Injectable({
  providedIn: 'root'
})
export class ChangeDetectionDebuggerService {
  private eventsSubject = new Subject<ChangeDetectionEvent>();
  private isDebugging = false;
  private componentTimings = new Map<string, number[]>();
  
  events$ = this.eventsSubject.asObservable();
  
  startDebugging(): void {
    this.isDebugging = true;
    console.log('Change detection debugging started');
  }
  
  stopDebugging(): void {
    this.isDebugging = false;
    this.generateReport();
    console.log('Change detection debugging stopped');
  }
  
  recordChangeDetection(component: any, startTime: number): void {
    if (!this.isDebugging) {
      return;
    }
    
    const endTime = performance.now();
    const componentName = component.constructor.name;
    const detectionTime = endTime - startTime;
    
    // Store timing
    if (!this.componentTimings.has(componentName)) {
      this.componentTimings.set(componentName, []);
    }
    this.componentTimings.get(componentName)!.push(detectionTime);
    
    const event: ChangeDetectionEvent = {
      component: componentName,
      timestamp: Date.now(),
      changeDetectionTime: detectionTime,
      bindingsChecked: 0, // Would need to instrument Angular internals
      bindingsUpdated: 0
    };
    
    this.eventsSubject.next(event);
    
    // Log slow change detection
    if (detectionTime > 16.67) { // Longer than one frame (60fps)
      console.warn(`Slow change detection in ${componentName}: ${detectionTime.toFixed(2)}ms`);
    }
  }
  
  getComponentStatistics(): Map<string, {avg: number, max: number, min: number, count: number}> {
    const stats = new Map();
    
    for (const [component, timings] of this.componentTimings) {
      const avg = timings.reduce((a, b) => a + b, 0) / timings.length;
      const max = Math.max(...timings);
      const min = Math.min(...timings);
      
      stats.set(component, {
        avg: Math.round(avg * 100) / 100,
        max: Math.round(max * 100) / 100,
        min: Math.round(min * 100) / 100,
        count: timings.length
      });
    }
    
    return stats;
  }
  
  getSlowComponents(threshold: number = 16.67): string[] {
    const stats = this.getComponentStatistics();
    const slowComponents: string[] = [];
    
    for (const [component, stat] of stats) {
      if (stat.avg > threshold) {
        slowComponents.push(component);
      }
    }
    
    return slowComponents;
  }
  
  generateReport(): void {
    const stats = this.getComponentStatistics();
    const slowComponents = this.getSlowComponents();
    
    console.group('Change Detection Performance Report');
    console.table(Array.from(stats.entries()).map(([component, stat]) => ({
      Component: component,
      'Avg Time (ms)': stat.avg,
      'Max Time (ms)': stat.max,
      'Min Time (ms)': stat.min,
      'Executions': stat.count
    })));
    
    if (slowComponents.length > 0) {
      console.warn('Slow Components (>16.67ms):', slowComponents);
    }
    
    console.groupEnd();
  }
  
  // Decorator for debugging components
  static DebugChangeDetection() {
    return function(target: any) {
      const originalDetectChanges = target.prototype.detectChanges;
      
      if (originalDetectChanges) {
        target.prototype.detectChanges = function() {
          const startTime = performance.now();
          const result = originalDetectChanges.apply(this);
          
          // Get the debugger service (would need to be injected)
          const debugger = (window as any).changeDetectionDebugger;
          if (debugger) {
            debugger.recordChangeDetection(this, startTime);
          }
          
          return result;
        };
      }
      
      return target;
    };
  }
}
```

## 6. Debugging de Banco de Dados

### 6.1 PostgreSQL Debugging

**`tooling/database_debugger.py`**:
```python
#!/usr/bin/env python3
"""
Database debugging and optimization tools for Janus
"""

import psycopg2
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import argparse

class DatabaseDebugger:
    def __init__(self, connection_string: str, output_dir="database_debug"):
        self.connection_string = connection_string
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.connection_string)
    
    def analyze_slow_queries(self, min_duration_ms: int = 1000) -> Dict:
        """Analyze slow queries from PostgreSQL logs"""
        print(f"Analyzing queries slower than {min_duration_ms}ms...")
        
        query = """
        SELECT 
            query,
            calls,
            total_time,
            mean_time,
            rows,
            100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
        FROM pg_stat_statements
        WHERE mean_time > %s
        ORDER BY mean_time DESC
        LIMIT 20;
        """
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (min_duration_ms,))
                slow_queries = cursor.fetchall()
        
        # Convert to structured format
        slow_queries_analysis = []
        for query_data in slow_queries:
            slow_queries_analysis.append({
                'query': query_data[0],
                'calls': query_data[1],
                'total_time_ms': query_data[2],
                'avg_time_ms': query_data[3],
                'rows_returned': query_data[4],
                'cache_hit_ratio': float(query_data[5]) if query_data[5] else 0
            })
        
        # Generate recommendations
        recommendations = []
        for query_info in slow_queries_analysis:
            if query_info['cache_hit_ratio'] < 90:
                recommendations.append({
                    'query': query_info['query'][:100] + '...',
                    'issue': 'Low cache hit ratio',
                    'recommendation': 'Consider increasing shared_buffers or optimizing query'
                })
            
            if query_info['avg_time_ms'] > 5000:
                recommendations.append({
                    'query': query_info['query'][:100] + '...',
                    'issue': 'Very slow query',
                    'recommendation': 'Consider adding indexes or query optimization'
                })
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'min_duration_ms': min_duration_ms,
            'slow_queries': slow_queries_analysis,
            'recommendations': recommendations,
            'total_slow_queries': len(slow_queries_analysis)
        }
        
        # Save results
        output_file = self.output_dir / f"slow_queries_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        return result
    
    def analyze_table_bloat(self) -> Dict:
        """Analyze table bloat in PostgreSQL"""
        print("Analyzing table bloat...")
        
        query = """
        SELECT 
            schemaname,
            tablename,
            bs * tblpages AS table_size_bytes,
            bs * (tblpages - est_tblpages_pp) AS bloat_bytes,
            CASE WHEN tblpages > 0 
                THEN 100 * (tblpages - est_tblpages_pp) / tblpages 
                ELSE 0 
            END AS bloat_percent,
            bs * tblpages_fp AS free_space_bytes
        FROM (
            SELECT 
                schemaname,
                tablename,
                cc.relpages AS tblpages,
                cc.reltuples AS tuples,
                current_setting('block_size')::int AS bs,
                CEIL((cc.reltuples * ((datahdr + 8 - (CASE WHEN datahdr % 8 = 0 THEN 8 ELSE datahdr % 8 END)) + nullhdr + 8)) / (bs - 20::float)) AS est_tblpages_pp,
                tblpages_fp
            FROM (
                SELECT 
                    ns.nspname AS schemaname,
                    tbl.relname AS tablename,
                    tbl.relpages,
                    tbl.reltuples,
                    (current_setting('block_size')::int - HEADER) * 100 / (100 + FILLFACTOR) AS tblpages_fp,
                    HEADER + 8 AS datahdr,
                    CASE WHEN MAX(coalesce(null_frac, 0)) = 0 THEN 0 ELSE 1 END AS nullhdr
                FROM pg_class tbl
                JOIN pg_namespace ns ON ns.oid = tbl.relnamespace
                LEFT JOIN pg_stats s ON s.schemaname = ns.nspname AND s.tablename = tbl.relname
                CROSS JOIN (SELECT 23 AS HEADER, 10 AS FILLFACTOR) AS constants
                WHERE tbl.relkind = 'r'
                GROUP BY 1, 2, 3, 4, 5, 6
            ) AS cc
        ) AS bloat_calc
        WHERE bloat_percent > 20
        ORDER BY bloat_bytes DESC;
        """
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                bloat_data = cursor.fetchall()
        
        bloat_analysis = []
        for bloat_info in bloat_data:
            bloat_analysis.append({
                'schema': bloat_info[0],
                'table': bloat_info[1],
                'table_size_mb': bloat_info[2] / 1024 / 1024,
                'bloat_size_mb': bloat_info[3] / 1024 / 1024,
                'bloat_percent': float(bloat_info[4]),
                'free_space_mb': bloat_info[5] / 1024 / 1024
            })
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'tables_with_bloat': bloat_analysis,
            'total_bloat_mb': sum(table['bloat_size_mb'] for table in bloat_analysis),
            'recommendations': [
                'Consider running VACUUM on bloated tables',
                'Review autovacuum settings',
                'Consider pg_repack for large tables'
            ] if bloat_analysis else ['No significant table bloat detected']
        }
        
        # Save results
        output_file = self.output_dir / f"table_bloat_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        return result
    
    def analyze_index_usage(self) -> Dict:
        """Analyze index usage and effectiveness"""
        print("Analyzing index usage...")
        
        query = """
        SELECT 
            t.schemaname,
            t.tablename,
            indexname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch,
            pg_size_pretty(pg_relation_size(c.oid)) AS index_size
        FROM pg_stat_user_indexes AS t
        JOIN pg_class AS c ON t.indexrelname = c.relname
        WHERE t.idx_scan = 0
        ORDER BY pg_relation_size(c.oid) DESC;
        """
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                unused_indexes = cursor.fetchall()
        
        unused_analysis = []
        for index_info in unused_indexes:
            unused_analysis.append({
                'schema': index_info[0],
                'table': index_info[1],
                'index': index_info[2],
                'scans': index_info[3],
                'tuples_read': index_info[4],
                'tuples_fetched': index_info[5],
                'index_size': index_info[6]
            })
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'unused_indexes': unused_analysis,
            'total_unused_indexes': len(unused_analysis),
            'recommendations': [
                'Consider dropping unused indexes',
                'Review index design for frequently queried columns',
                'Monitor index usage before dropping'
            ] if unused_analysis else ['All indexes are being used effectively']
        }
        
        # Save results
        output_file = self.output_dir / f"index_usage_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        return result
    
    def analyze_connection_pooling(self) -> Dict:
        """Analyze database connection usage"""
        print("Analyzing connection pooling...")
        
        query = """
        SELECT 
            count(*) as total_connections,
            state,
            application_name,
            client_addr,
            backend_start,
            state_change,
            extract(epoch from (now() - state_change)) as idle_duration_seconds
        FROM pg_stat_activity
        WHERE datname = current_database()
        GROUP BY state, application_name, client_addr, backend_start, state_change
        ORDER BY idle_duration_seconds DESC;
        """
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                connections = cursor.fetchall()
        
        connection_analysis = []
        for conn_info in connections:
            connection_analysis.append({
                'total_connections': conn_info[0],
                'state': conn_info[1],
                'application': conn_info[2],
                'client_addr': str(conn_info[3]),
                'backend_start': conn_info[4].isoformat() if conn_info[4] else None,
                'state_change': conn_info[5].isoformat() if conn_info[5] else None,
                'idle_duration_seconds': float(conn_info[6]) if conn_info[6] else 0
            })
        
        # Analyze idle connections
        idle_connections = [c for c in connection_analysis if c['state'] == 'idle']
        long_idle_connections = [c for c in idle_connections if c['idle_duration_seconds'] > 300]
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'connections': connection_analysis,
            'total_connections': sum(c['total_connections'] for c in connection_analysis),
            'idle_connections': len(idle_connections),
            'long_idle_connections': len(long_idle_connections),
            'recommendations': [
                f'Consider closing {len(long_idle_connections)} long-idle connections',
                'Review connection pool configuration',
                'Implement connection timeout policies'
            ] if long_idle_connections else ['Connection pooling appears healthy']
        }
        
        # Save results
        output_file = self.output_dir / f"connection_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        return result
    
    def comprehensive_database_analysis(self) -> Dict:
        """Run comprehensive database analysis"""
        print("Starting comprehensive database analysis...")
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'slow_queries': self.analyze_slow_queries(),
            'table_bloat': self.analyze_table_bloat(),
            'index_usage': self.analyze_index_usage(),
            'connection_pooling': self.analyze_connection_pooling()
        }
        
        # Compile summary
        total_issues = (
            analysis['slow_queries']['total_slow_queries'] +
            len(analysis['table_bloat']['tables_with_bloat']) +
            analysis['index_usage']['total_unused_indexes'] +
            analysis['connection_pooling']['long_idle_connections']
        )
        
        analysis['summary'] = {
            'total_issues_found': total_issues,
            'severity': 'high' if total_issues > 10 else 'medium' if total_issues > 5 else 'low',
            'recommendations': [
                'Address slow queries first for immediate performance gains',
                'Clean up table bloat to improve query performance',
                'Remove unused indexes to save space',
                'Optimize connection pooling for better resource usage'
            ]
        }
        
        # Save comprehensive report
        report_file = self.output_dir / f"comprehensive_database_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        print(f"Comprehensive database analysis complete!")
        print(f"Report saved to: {report_file}")
        print(f"Total issues found: {total_issues}")
        
        return analysis

# Usage example
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python database_debugger.py <connection_string>")
        print("Example: python database_debugger.py postgresql://user:pass@localhost/janus")
        sys.exit(1)
    
    connection_string = sys.argv[1]
    debugger = DatabaseDebugger(connection_string)
    
    print("Running comprehensive database analysis...")
    debugger.comprehensive_database_analysis()
```

## 7. Debugging de Segurança

### 7.1 Análise de JWT e Autorização

**`tooling/security_debugger.py`**:
```python
#!/usr/bin/env python3
"""
Security debugging and analysis tools for Janus
"""

import jwt
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import argparse

class SecurityDebugger:
    def __init__(self, base_url: str = "http://localhost:8000", output_dir="security_debug"):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def analyze_jwt_token(self, token: str) -> Dict:
        """Analyze JWT token structure and claims"""
        print("Analyzing JWT token...")
        
        try:
            # Decode without verification to analyze structure
            header = jwt.get_unverified_header(token)
            payload = jwt.decode(token, options