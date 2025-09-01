# cache_cli.py
# Self-Contained Cache Management CLI for Universal Engine
# Built-in configuration defaults with optional .env overrides
#
# USAGE:
# python -m flask --app cache_cli.py cache stats
# python -m flask --app cache_cli.py cache live
# python -m flask --app cache_cli.py cache health

# View configuration
# python -m flask --app cache_cli.py cache config

# View comprehensive dashboard
# python -m flask --app cache_cli.py cache stats

# Live monitoring
# python -m flask --app cache_cli.py cache live

# Health check
# python -m flask --app cache_cli.py cache health

# Interactive dashboard
# python -m flask --app cache_cli.py cache monitor --dashboard

# Memory analysis
# python -m flask --app cache_cli.py cache memory-analysis

# Clear caches
# python -m flask --app cache_cli.py cache clear

# Help for all commands
# python -m flask --app cache_cli.py cache --help

import os
import sys
import time
import json
import click
from datetime import datetime, timedelta
from flask import Flask, current_app
from flask.cli import with_appcontext
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.info("python-dotenv not available, using environment variables only")

# ============================================================================
# CACHE CONFIGURATION WITH SMART DEFAULTS
# ============================================================================

class CacheConfig:
    """Self-contained cache configuration with smart defaults"""
    
    # ✅ SERVICE CACHE DEFAULTS (Primary Layer)
    SERVICE_CACHE_ENABLED = False
    SERVICE_CACHE_MAX_MEMORY_MB = 500
    SERVICE_CACHE_DEFAULT_TTL = 1800  # 30 minutes
    SERVICE_CACHE_MAX_ENTRIES = 10000
    
    # ✅ CONFIG CACHE DEFAULTS (Secondary Layer)  
    CONFIG_CACHE_ENABLED = False
    CONFIG_CACHE_PRELOAD = True
    CONFIG_CACHE_TTL = 3600  # 1 hour
    
    # ✅ MONITORING DEFAULTS
    CACHE_MONITORING_ENABLED = True
    CACHE_LIVE_REFRESH_SECONDS = 5
    CACHE_DEBUG_LOGGING = False
    
    # ✅ PERFORMANCE THRESHOLDS
    CACHE_HEALTH_SERVICE_HIT_MIN = 0.80
    CACHE_HEALTH_CONFIG_HIT_MIN = 0.95
    CACHE_HEALTH_MEMORY_MAX = 0.85
    CACHE_HEALTH_RESPONSE_MAX = 100  # milliseconds
    
    @classmethod
    def get_setting(cls, key: str, default=None):
        """Get setting from environment or use built-in default"""
        
        # Map of settings to defaults
        defaults = {
            'SERVICE_CACHE_ENABLED': cls.SERVICE_CACHE_ENABLED,
            'SERVICE_CACHE_MAX_MEMORY_MB': cls.SERVICE_CACHE_MAX_MEMORY_MB,
            'SERVICE_CACHE_DEFAULT_TTL': cls.SERVICE_CACHE_DEFAULT_TTL,
            'SERVICE_CACHE_MAX_ENTRIES': cls.SERVICE_CACHE_MAX_ENTRIES,
            'CONFIG_CACHE_ENABLED': cls.CONFIG_CACHE_ENABLED,
            'CONFIG_CACHE_PRELOAD': cls.CONFIG_CACHE_PRELOAD,
            'CONFIG_CACHE_TTL': cls.CONFIG_CACHE_TTL,
            'CACHE_MONITORING_ENABLED': cls.CACHE_MONITORING_ENABLED,
            'CACHE_LIVE_REFRESH_SECONDS': cls.CACHE_LIVE_REFRESH_SECONDS,
            'CACHE_DEBUG_LOGGING': cls.CACHE_DEBUG_LOGGING,
            'CACHE_HEALTH_SERVICE_HIT_MIN': cls.CACHE_HEALTH_SERVICE_HIT_MIN,
            'CACHE_HEALTH_CONFIG_HIT_MIN': cls.CACHE_HEALTH_CONFIG_HIT_MIN,
            'CACHE_HEALTH_MEMORY_MAX': cls.CACHE_HEALTH_MEMORY_MAX,
            'CACHE_HEALTH_RESPONSE_MAX': cls.CACHE_HEALTH_RESPONSE_MAX,
        }
        
        # Check environment first, then use default
        env_value = os.getenv(key)
        if env_value is not None:
            # Convert based on default type
            default_val = defaults.get(key, default)
            if isinstance(default_val, bool):
                return env_value.lower() in ('true', '1', 'yes', 'on')
            elif isinstance(default_val, int):
                try:
                    return int(env_value)
                except ValueError:
                    return default_val
            elif isinstance(default_val, float):
                try:
                    return float(env_value)
                except ValueError:
                    return default_val
            return env_value
        
        return defaults.get(key, default)

# Create Flask app
app = Flask(__name__)

def configure_cache_app():
    """Configure Flask app with cache settings"""
    
    # Database configuration (required for cache CLI to work with your models)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_dev'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # ✅ CACHE CONFIGURATION using smart defaults
    app.config['SERVICE_CACHE_ENABLED'] = CacheConfig.get_setting('SERVICE_CACHE_ENABLED')
    app.config['SERVICE_CACHE_MAX_MEMORY_MB'] = CacheConfig.get_setting('SERVICE_CACHE_MAX_MEMORY_MB')
    app.config['SERVICE_CACHE_DEFAULT_TTL'] = CacheConfig.get_setting('SERVICE_CACHE_DEFAULT_TTL')
    app.config['SERVICE_CACHE_MAX_ENTRIES'] = CacheConfig.get_setting('SERVICE_CACHE_MAX_ENTRIES')
    
    app.config['CONFIG_CACHE_ENABLED'] = CacheConfig.get_setting('CONFIG_CACHE_ENABLED')
    app.config['CONFIG_CACHE_PRELOAD'] = CacheConfig.get_setting('CONFIG_CACHE_PRELOAD')
    app.config['CONFIG_CACHE_TTL'] = CacheConfig.get_setting('CONFIG_CACHE_TTL')
    
    app.config['CACHE_MONITORING_ENABLED'] = CacheConfig.get_setting('CACHE_MONITORING_ENABLED')
    app.config['CACHE_LIVE_REFRESH_SECONDS'] = CacheConfig.get_setting('CACHE_LIVE_REFRESH_SECONDS')

# Configure the app
configure_cache_app()

# ============================================================================
# CACHE CLI COMMANDS
# ============================================================================

@click.group()
def cache():
    """Universal Engine cache management commands"""
    pass

@cache.command()
@with_appcontext
def config():
    """Display current cache configuration"""
    click.echo("\n🔧 UNIVERSAL ENGINE CACHE CONFIGURATION")
    click.echo("="*60)
    
    # Configuration Sources
    click.echo("📋 CONFIGURATION SOURCES:")
    click.echo("   1. Built-in defaults (CacheConfig class)")
    click.echo("   2. Environment variables (.env file)")
    click.echo("   3. Command-line overrides")
    
    # Current Settings
    click.echo(f"\n⚙️  CURRENT SETTINGS:")
    
    config_items = [
        ('SERVICE_CACHE_ENABLED', 'Service Cache'),
        ('SERVICE_CACHE_MAX_MEMORY_MB', 'Memory Limit (MB)'),
        ('SERVICE_CACHE_DEFAULT_TTL', 'Default TTL (seconds)'),
        ('CONFIG_CACHE_ENABLED', 'Config Cache'),
        ('CONFIG_CACHE_PRELOAD', 'Preload Configs'),
        ('CACHE_MONITORING_ENABLED', 'Monitoring'),
        ('CACHE_LIVE_REFRESH_SECONDS', 'Live Refresh (s)')
    ]
    
    for key, label in config_items:
        value = current_app.config.get(key, 'NOT SET')
        env_override = '🌐' if os.getenv(key) else '⚙️'
        click.echo(f"   {env_override} {label:<25}: {value}")
    
    click.echo(f"\n💡 LEGEND:")
    click.echo(f"   ⚙️  Built-in default value")
    click.echo(f"   🌐 Environment variable override")
    
    # Environment Override Instructions
    click.echo(f"\n📝 TO CUSTOMIZE SETTINGS:")
    click.echo(f"   Add to your .env file (only the ones you want to change):")
    click.echo(f"   SERVICE_CACHE_MAX_MEMORY_MB=1000    # Increase memory limit")
    click.echo(f"   CACHE_LIVE_REFRESH_SECONDS=3        # Faster refresh rate")
    click.echo(f"   SERVICE_CACHE_ENABLED=false         # Disable service cache")
    
    click.echo("="*60)

@cache.command()
@with_appcontext
def stats():
    """Display comprehensive cache statistics"""
    try:
        from app.engine.universal_service_cache import get_service_cache_manager
        from app.engine.universal_config_cache import get_cached_configuration_loader
        
        service_cache = get_service_cache_manager()
        config_cache = get_cached_configuration_loader()
        
        service_stats = service_cache.get_cache_statistics()
        config_stats = config_cache.get_cache_statistics()
        
        click.echo("\n" + "="*70)
        click.echo("🏥 SKINSPIRE HMS - CACHE PERFORMANCE DASHBOARD")
        click.echo("="*70)
        
        # Service Cache Performance
        click.echo(f"🚀 SERVICE CACHE (Database Operations)")
        click.echo(f"   Hit Ratio: {service_stats['hit_ratio']:.2%} (Target: >{CacheConfig.get_setting('CACHE_HEALTH_SERVICE_HIT_MIN'):.0%})")
        click.echo(f"   Total Hits: {service_stats['total_hits']:,}")
        click.echo(f"   Total Misses: {service_stats['total_misses']:,}")
        click.echo(f"   Memory: {service_stats['memory_usage_mb']:.1f}MB / {service_stats['max_memory_mb']:.0f}MB")
        click.echo(f"   Avg Response: {service_stats['avg_response_time_ms']:.1f}ms")
        click.echo(f"   Requests/Min: {service_stats.get('requests_per_minute', 0):.1f}")
        
        # Configuration Cache Performance
        click.echo(f"\n🔧 CONFIG CACHE (Entity Configurations)")
        click.echo(f"   Hit Ratio: {config_stats['hit_ratio']:.2%} (Target: >{CacheConfig.get_setting('CACHE_HEALTH_CONFIG_HIT_MIN'):.0%})")
        click.echo(f"   Total Hits: {config_stats['total_hits']:,}")
        click.echo(f"   Total Misses: {config_stats['total_misses']:,}")
        click.echo(f"   Cached Configs: {config_stats['total_cached_configs']}")
        click.echo(f"   Memory: {config_stats.get('memory_usage_mb', 0):.1f}MB")
        
        # Entity Performance (if available)
        if 'entity_stats' in service_stats and service_stats['entity_stats']:
            click.echo(f"\n📊 TOP PERFORMING ENTITIES:")
            sorted_entities = sorted(
                service_stats['entity_stats'].items(),
                key=lambda x: x[1].get('hits', 0),
                reverse=True
            )[:5]
            
            for entity, stats in sorted_entities:
                click.echo(f"   {entity:<15}: {stats['hits']:>4} hits ({stats.get('hit_ratio', 0):.1%})")
        
        # Overall Performance Assessment
        overall_ratio = (service_stats['hit_ratio'] + config_stats['hit_ratio']) / 2
        if overall_ratio > 0.90:
            status = "🟢 EXCELLENT"
        elif overall_ratio > 0.80:
            status = "🟡 GOOD"
        else:
            status = "🔴 NEEDS ATTENTION"
        
        click.echo(f"\n📈 OVERALL PERFORMANCE: {status} ({overall_ratio:.1%})")
        click.echo("="*70)
        
    except Exception as e:
        click.echo(f"❌ Error getting cache statistics: {str(e)}")
        logger.error(f"Cache stats error: {e}")

@cache.command()
@with_appcontext
def live():
    """Enhanced live cache dashboard with comprehensive monitoring"""
    refresh_interval = CacheConfig.get_setting('CACHE_LIVE_REFRESH_SECONDS')
    
    click.echo(f"🏥 SKINSPIRE HMS - LIVE CACHE DASHBOARD")
    click.echo("="*85)
    click.echo(f"📊 Real-time monitoring (refresh: {refresh_interval}s) - Press Ctrl+C to stop")
    click.echo("="*85)
    
    # Track performance history for trending
    performance_history = []
    iteration = 0
    
    try:
        while True:
            iteration += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            try:
                from app.engine.universal_service_cache import get_service_cache_manager
                from app.engine.universal_config_cache import get_cached_configuration_loader
                
                service_cache = get_service_cache_manager()
                config_cache = get_cached_configuration_loader()
                
                service_stats = service_cache.get_cache_statistics()
                config_stats = config_cache.get_cache_statistics()
                
                # Store for trending
                performance_history.append({
                    'timestamp': datetime.now(),
                    'service_hit_ratio': service_stats['hit_ratio'],
                    'memory_usage': service_stats['memory_usage_mb'],
                    'requests_per_min': service_stats.get('requests_per_minute', 0)
                })
                
                # Keep only last 20 entries for trending
                if len(performance_history) > 20:
                    performance_history.pop(0)
                
                # Clear screen every 20 iterations for dashboard effect
                if iteration % 20 == 1:
                    os.system('clear' if os.name == 'posix' else 'cls')
                    click.echo(f"🏥 SKINSPIRE HMS - LIVE CACHE DASHBOARD")
                    click.echo("="*85)
                
                # Current Performance Header
                click.echo(f"\n[{timestamp}] 📊 REAL-TIME PERFORMANCE (Update #{iteration})")
                click.echo("-" * 85)
                
                # Service Cache Performance
                memory_ratio = service_stats['memory_usage_mb'] / service_stats['max_memory_mb']
                memory_status = "🔴" if memory_ratio > 0.90 else "🟡" if memory_ratio > 0.75 else "🟢"
                
                hit_status = "🟢" if service_stats['hit_ratio'] > 0.90 else "🟡" if service_stats['hit_ratio'] > 0.80 else "🔴"
                
                click.echo(f"🚀 SERVICE CACHE | "
                          f"Hits: {service_stats['total_hits']:>7,} | "
                          f"Ratio: {hit_status}{service_stats['hit_ratio']:>6.1%} | "
                          f"Memory: {memory_status}{service_stats['memory_usage_mb']:>6.1f}MB | "
                          f"Resp: {service_stats['avg_response_time_ms']:>5.1f}ms | "
                          f"Req/Min: {service_stats.get('requests_per_minute', 0):>5.1f}")
                
                # Config Cache Performance
                config_hit_status = "🟢" if config_stats['hit_ratio'] > 0.95 else "🟡" if config_stats['hit_ratio'] > 0.85 else "🔴"
                
                click.echo(f"🔧 CONFIG CACHE  | "
                          f"Hits: {config_stats['total_hits']:>7,} | "
                          f"Ratio: {config_hit_status}{config_stats['hit_ratio']:>6.1%} | "
                          f"Configs: {config_stats['total_cached_configs']:>4} | "
                          f"Memory: {config_stats.get('memory_usage_mb', 0):>5.1f}MB")
                
                # Entity-Specific Performance (if available)
                if 'entity_stats' in service_stats and service_stats['entity_stats']:
                    click.echo(f"\n🎯 ENTITY PERFORMANCE:")
                    sorted_entities = sorted(
                        service_stats['entity_stats'].items(),
                        key=lambda x: x[1].get('hits', 0),
                        reverse=True
                    )[:5]  # Top 5 entities
                    
                    for entity, stats in sorted_entities:
                        entity_hit_status = "🟢" if stats.get('hit_ratio', 0) > 0.85 else "🟡" if stats.get('hit_ratio', 0) > 0.70 else "🔴"
                        click.echo(f"   {entity_hit_status} {entity:<15}: {stats['hits']:>4} hits ({stats.get('hit_ratio', 0):.1%} ratio)")
                
                # Performance Trending (if enough history)
                if len(performance_history) >= 5:
                    recent_avg = sum(p['service_hit_ratio'] for p in performance_history[-5:]) / 5
                    older_avg = sum(p['service_hit_ratio'] for p in performance_history[:5]) / 5
                    
                    if recent_avg > older_avg + 0.02:
                        trend = "📈 IMPROVING"
                    elif recent_avg < older_avg - 0.02:
                        trend = "📉 DECLINING" 
                    else:
                        trend = "➡️ STABLE"
                    
                    click.echo(f"\n📊 PERFORMANCE TREND: {trend} (Recent: {recent_avg:.1%})")
                
                # Overall System Status
                overall_ratio = (service_stats['hit_ratio'] + config_stats['hit_ratio']) / 2
                if overall_ratio > 0.90:
                    overall_status = "🟢 EXCELLENT"
                elif overall_ratio > 0.80:
                    overall_status = "🟡 GOOD"
                else:
                    overall_status = "🔴 NEEDS ATTENTION"
                
                uptime = service_stats.get('uptime_hours', 0)
                click.echo(f"\n📈 SYSTEM STATUS: {overall_status} | Overall: {overall_ratio:.1%} | Uptime: {uptime:.1f}h")
                
                # Memory Analysis
                if memory_ratio > 0.85:
                    click.echo(f"⚠️  HIGH MEMORY USAGE: {memory_ratio:.1%} - Consider running cleanup")
                
                click.echo("=" * 85)
                
            except Exception as e:
                click.echo(f"[{timestamp}] ❌ Error getting stats: {str(e)}")
            
            time.sleep(refresh_interval)
            
    except KeyboardInterrupt:
        # Performance summary on exit
        click.echo(f"\n\n📊 SESSION SUMMARY:")
        if len(performance_history) > 1:
            session_start = performance_history[0]['timestamp']
            session_end = performance_history[-1]['timestamp']
            session_duration = (session_end - session_start).total_seconds() / 60
            
            avg_hit_ratio = sum(p['service_hit_ratio'] for p in performance_history) / len(performance_history)
            avg_memory = sum(p['memory_usage'] for p in performance_history) / len(performance_history)
            avg_requests = sum(p['requests_per_min'] for p in performance_history) / len(performance_history)
            
            click.echo(f"   Session Duration: {session_duration:.1f} minutes")
            click.echo(f"   Average Hit Ratio: {avg_hit_ratio:.2%}")
            click.echo(f"   Average Memory: {avg_memory:.1f}MB")
            click.echo(f"   Average Requests: {avg_requests:.1f}/min")
            click.echo(f"   Total Updates: {len(performance_history)}")
        
        click.echo(f"✅ Live dashboard monitoring stopped")

@cache.command()
@with_appcontext
def health():
    """Cache system health check with smart thresholds"""
    try:
        from app.engine.universal_service_cache import get_service_cache_manager
        from app.engine.universal_config_cache import get_cached_configuration_loader
        
        service_cache = get_service_cache_manager()
        config_cache = get_cached_configuration_loader()
        
        service_stats = service_cache.get_cache_statistics()
        config_stats = config_cache.get_cache_statistics()
        
        click.echo("\n🏥 SKINSPIRE HMS - CACHE HEALTH CHECK")
        click.echo("="*50)
        
        # Health Assessment using built-in thresholds
        issues = []
        warnings = []
        
        # Service Cache Health
        service_hit_threshold = CacheConfig.get_setting('CACHE_HEALTH_SERVICE_HIT_MIN')
        if service_stats['hit_ratio'] < service_hit_threshold:
            issues.append(f"Service hit ratio: {service_stats['hit_ratio']:.1%} (min: {service_hit_threshold:.0%})")
        
        # Memory Usage
        memory_threshold = CacheConfig.get_setting('CACHE_HEALTH_MEMORY_MAX')
        memory_ratio = service_stats['memory_usage_mb'] / service_stats['max_memory_mb']
        if memory_ratio > memory_threshold:
            if memory_ratio > 0.95:
                issues.append(f"Critical memory usage: {memory_ratio:.1%}")
            else:
                warnings.append(f"High memory usage: {memory_ratio:.1%}")
        
        # Response Time
        response_threshold = CacheConfig.get_setting('CACHE_HEALTH_RESPONSE_MAX')
        if service_stats['avg_response_time_ms'] > response_threshold:
            issues.append(f"Slow response time: {service_stats['avg_response_time_ms']:.1f}ms")
        
        # Config Cache Health
        config_hit_threshold = CacheConfig.get_setting('CACHE_HEALTH_CONFIG_HIT_MIN')
        if config_stats['hit_ratio'] < config_hit_threshold:
            issues.append(f"Config hit ratio: {config_stats['hit_ratio']:.1%} (min: {config_hit_threshold:.0%})")
        
        # Display Results
        if not issues and not warnings:
            click.echo("✅ ALL HEALTH CHECKS PASSED")
            click.echo("   🚀 Service cache: EXCELLENT")
            click.echo("   🔧 Config cache: EXCELLENT")
            click.echo("   💾 Memory usage: OPTIMAL")
            click.echo("   ⚡ Response times: FAST")
        else:
            if issues:
                click.echo("❌ CRITICAL ISSUES:")
                for issue in issues:
                    click.echo(f"   🚨 {issue}")
            
            if warnings:
                click.echo("⚠️ WARNINGS:")
                for warning in warnings:
                    click.echo(f"   ⚠️  {warning}")
            
            # Recommendations
            click.echo(f"\n💡 RECOMMENDATIONS:")
            if any('memory' in issue.lower() for issue in issues + warnings):
                click.echo("   • Run 'flask cache cleanup' to free memory")
                click.echo("   • Consider increasing SERVICE_CACHE_MAX_MEMORY_MB")
            if any('hit ratio' in issue.lower() for issue in issues):
                click.echo("   • Run 'flask cache warm' to improve hit ratios")
                click.echo("   • Check if cache TTL settings are appropriate")
        
        # System Status Summary
        uptime_hours = service_stats.get('uptime_hours', 0)
        total_requests = service_stats['total_hits'] + service_stats['total_misses']
        
        click.echo(f"\n📊 SYSTEM STATUS:")
        click.echo(f"   Uptime: {uptime_hours:.1f} hours")
        click.echo(f"   Total Requests: {total_requests:,}")
        click.echo(f"   Overall Hit Ratio: {(service_stats['hit_ratio'] + config_stats['hit_ratio']) / 2:.1%}")
        
        click.echo("="*50)
        
    except Exception as e:
        click.echo(f"❌ Health check failed: {str(e)}")

@cache.command()
@click.argument('entity_type')
@with_appcontext
def invalidate(entity_type):
    """Invalidate cache for specific entity type"""
    try:
        from app.engine.universal_service_cache import get_service_cache_manager
        
        service_cache = get_service_cache_manager()
        entries = service_cache.invalidate_entity_cache(entity_type, cascade=True)
        
        click.echo(f"✅ Cache invalidation completed for '{entity_type}'")
        click.echo(f"   🗑️ Service cache: {entries} entries invalidated")
        
        # Show cascade effects if any
        if entries > 1:
            click.echo(f"   🔄 Cascade invalidation triggered for related entities")
        
    except Exception as e:
        click.echo(f"❌ Error invalidating cache: {str(e)}")

@cache.command()
@with_appcontext
def clear():
    """Clear all cache layers"""
    try:
        from app.engine.universal_service_cache import get_service_cache_manager
        
        service_cache = get_service_cache_manager()
        service_entries = service_cache.clear_all_cache()
        
        # Try to clear config cache if available
        config_entries = 0
        try:
            from app.engine.universal_config_cache import get_cached_configuration_loader
            config_cache = get_cached_configuration_loader()
            if hasattr(config_cache, 'clear_all_config_cache'):
                config_entries = config_cache.clear_all_config_cache()
        except (ImportError, AttributeError):
            pass
        
        click.echo("🧹 CACHE CLEARANCE COMPLETED:")
        click.echo(f"   🚀 Service cache: {service_entries} entries cleared")
        if config_entries:
            click.echo(f"   🔧 Config cache: {config_entries} entries cleared")
        click.echo("   ✅ All caches are now empty")
        
    except Exception as e:
        click.echo(f"❌ Error clearing caches: {str(e)}")

@cache.command()
@with_appcontext
def warm():
    """Warm up cache layers"""
    try:
        config_count = 0
        
        # Warm configuration cache if enabled
        if current_app.config.get('CONFIG_CACHE_ENABLED'):
            try:
                from app.engine.universal_config_cache import preload_common_configurations
                config_count = preload_common_configurations()
                click.echo(f"✅ Configuration cache warmed: {config_count} configs preloaded")
            except ImportError:
                click.echo("⚠️  Config cache module not available")
        
        click.echo("ℹ️  Service cache will warm naturally on first requests")
        
        # Suggest warmup requests
        click.echo("\n🔥 SUGGESTED WARMUP REQUESTS:")
        common_entities = ['suppliers', 'patients', 'medicines', 'users', 'staff']
        for entity in common_entities:
            click.echo(f"   curl http://localhost:5000/universal/{entity}/list")
        
    except Exception as e:
        click.echo(f"❌ Error warming up caches: {str(e)}")

@cache.command()
@click.option('--format', type=click.Choice(['json', 'csv', 'detailed']), default='json', help='Export format')
@click.option('--include-history', is_flag=True, help='Include historical performance data')
@with_appcontext
def export_stats(format, include_history):
    """Export comprehensive cache statistics with advanced analysis"""
    try:
        from app.engine.universal_service_cache import get_service_cache_manager
        from app.engine.universal_config_cache import get_cached_configuration_loader
        
        service_cache = get_service_cache_manager()
        config_cache = get_cached_configuration_loader()
        
        service_stats = service_cache.get_cache_statistics()
        config_stats = config_cache.get_cache_statistics()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == 'detailed':
            # Comprehensive analysis export
            filename = f"cache_analysis_{timestamp}.json"
            export_data = {
                'export_info': {
                    'timestamp': datetime.now().isoformat(),
                    'skinspire_version': 'v3.1',
                    'universal_engine': 'v3.1',
                    'export_type': 'comprehensive_analysis'
                },
                'performance_summary': {
                    'overall_hit_ratio': (service_stats['hit_ratio'] + config_stats['hit_ratio']) / 2,
                    'performance_grade': _calculate_performance_grade(service_stats, config_stats),
                    'recommendations': _generate_performance_recommendations(service_stats, config_stats)
                },
                'service_cache': service_stats,
                'config_cache': config_stats,
                'system_analysis': {
                    'memory_efficiency': service_stats['memory_usage_mb'] / service_stats['max_memory_mb'],
                    'cache_effectiveness': _analyze_cache_effectiveness(service_stats),
                    'optimization_opportunities': _identify_optimization_opportunities(service_stats, config_stats)
                },
                'configuration': {
                    key: current_app.config.get(key) 
                    for key in current_app.config 
                    if key.startswith(('CACHE_', 'SERVICE_CACHE_', 'CONFIG_CACHE_'))
                }
            }
            
            if include_history:
                export_data['historical_analysis'] = _get_historical_analysis(service_cache)
                
        elif format == 'csv':
            # CSV format for spreadsheet analysis
            filename = f"cache_stats_{timestamp}.csv"
            csv_data = _format_stats_as_csv(service_stats, config_stats)
            with open(filename, 'w') as f:
                f.write(csv_data)
            
        else:  # json
            filename = f"cache_stats_{timestamp}.json"
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'service_cache': service_stats,
                'config_cache': config_stats,
                'configuration': {
                    key: current_app.config.get(key) 
                    for key in current_app.config 
                    if key.startswith(('CACHE_', 'SERVICE_CACHE_', 'CONFIG_CACHE_'))
                }
            }
        
        # Write file (for json and detailed)
        if format in ['json', 'detailed']:
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
        
        click.echo(f"✅ Cache statistics exported to {filename}")
        
        # Show summary of what was exported
        if format == 'detailed':
            click.echo(f"📊 EXPORT INCLUDES:")
            click.echo(f"   • Comprehensive performance analysis")
            click.echo(f"   • Optimization recommendations") 
            click.echo(f"   • System efficiency metrics")
            click.echo(f"   • Entity-specific performance data")
            if include_history:
                click.echo(f"   • Historical trend analysis")
        
    except Exception as e:
        click.echo(f"❌ Export failed: {str(e)}")

def _calculate_performance_grade(service_stats: dict, config_stats: dict) -> str:
    """Calculate overall performance grade"""
    overall_ratio = (service_stats['hit_ratio'] + config_stats['hit_ratio']) / 2
    memory_efficiency = 1 - (service_stats['memory_usage_mb'] / service_stats['max_memory_mb'])
    response_score = max(0, 1 - (service_stats['avg_response_time_ms'] / 200))  # 200ms baseline
    
    total_score = (overall_ratio * 0.6) + (memory_efficiency * 0.2) + (response_score * 0.2)
    
    if total_score > 0.90:
        return "A+ (Excellent)"
    elif total_score > 0.80:
        return "A (Very Good)"
    elif total_score > 0.70:
        return "B (Good)"
    elif total_score > 0.60:
        return "C (Fair)"
    else:
        return "D (Needs Improvement)"

def _generate_performance_recommendations(service_stats: dict, config_stats: dict) -> list:
    """Generate specific performance recommendations"""
    recommendations = []
    
    if service_stats['hit_ratio'] < 0.85:
        recommendations.append("Increase SERVICE_CACHE_DEFAULT_TTL to improve hit ratio")
    
    memory_ratio = service_stats['memory_usage_mb'] / service_stats['max_memory_mb']
    if memory_ratio > 0.85:
        recommendations.append("Increase SERVICE_CACHE_MAX_MEMORY_MB or run cleanup more frequently")
    
    if service_stats['avg_response_time_ms'] > 100:
        recommendations.append("Check database performance and query optimization")
    
    if config_stats['hit_ratio'] < 0.95:
        recommendations.append("Enable CONFIG_CACHE_PRELOAD for better configuration cache performance")
    
    if service_stats.get('requests_per_minute', 0) < 1:
        recommendations.append("System may benefit from cache warming strategies")
    
    if not recommendations:
        recommendations.append("Performance is optimal - no immediate improvements needed")
    
    return recommendations

def _analyze_cache_effectiveness(service_stats: dict) -> dict:
    """Analyze cache effectiveness metrics"""
    total_requests = service_stats['total_hits'] + service_stats['total_misses']
    
    return {
        'hit_efficiency': service_stats['hit_ratio'],
        'memory_efficiency': 1 - (service_stats['memory_usage_mb'] / service_stats['max_memory_mb']),
        'response_efficiency': max(0, 1 - (service_stats['avg_response_time_ms'] / 200)),
        'request_volume': total_requests,
        'cache_utilization': service_stats['memory_usage_mb'] / service_stats['max_memory_mb']
    }

def _identify_optimization_opportunities(service_stats: dict, config_stats: dict) -> list:
    """Identify specific optimization opportunities"""
    opportunities = []
    
    # Memory optimization
    memory_ratio = service_stats['memory_usage_mb'] / service_stats['max_memory_mb']
    if memory_ratio < 0.50:
        opportunities.append("Memory underutilized - could increase cache size for better performance")
    elif memory_ratio > 0.90:
        opportunities.append("Memory near limit - consider cleanup or increasing limit")
    
    # Hit ratio optimization
    if service_stats['hit_ratio'] < 0.90:
        opportunities.append("Hit ratio could be improved with longer TTL or cache warming")
    
    # Entity-specific optimization
    if 'entity_stats' in service_stats:
        low_performing_entities = [
            entity for entity, stats in service_stats['entity_stats'].items()
            if stats.get('hit_ratio', 0) < 0.70
        ]
        if low_performing_entities:
            opportunities.append(f"Entities with low hit ratios: {', '.join(low_performing_entities)}")
    
    return opportunities

def _get_historical_analysis(service_cache) -> dict:
    """Get historical performance analysis if available"""
    # This would require the cache to track historical data
    # For now, return current snapshot analysis
    return {
        'note': 'Historical analysis requires extended monitoring session',
        'recommendation': 'Use live dashboard for 30+ minutes to collect trend data'
    }

def _format_stats_as_csv(service_stats: dict, config_stats: dict) -> str:
    """Format statistics as CSV for spreadsheet analysis"""
    lines = []
    lines.append("Metric,Service_Cache,Config_Cache,Combined")
    lines.append(f"Hit_Ratio,{service_stats['hit_ratio']:.4f},{config_stats['hit_ratio']:.4f},{(service_stats['hit_ratio'] + config_stats['hit_ratio']) / 2:.4f}")
    lines.append(f"Total_Hits,{service_stats['total_hits']},{config_stats['total_hits']},{service_stats['total_hits'] + config_stats['total_hits']}")
    lines.append(f"Total_Misses,{service_stats['total_misses']},{config_stats['total_misses']},{service_stats['total_misses'] + config_stats['total_misses']}")
    lines.append(f"Memory_MB,{service_stats['memory_usage_mb']:.2f},{config_stats.get('memory_usage_mb', 0):.2f},{service_stats['memory_usage_mb'] + config_stats.get('memory_usage_mb', 0):.2f}")
    lines.append(f"Avg_Response_MS,{service_stats['avg_response_time_ms']:.2f},N/A,{service_stats['avg_response_time_ms']:.2f}")
    
    return "\n".join(lines)

@cache.command()
@click.option('--threshold', type=float, default=0.85, help='Memory usage threshold (0.0-1.0)')
@click.option('--detailed', is_flag=True, help='Show detailed memory breakdown')
@with_appcontext
def memory_analysis(threshold, detailed):
    """Advanced cache memory analysis with optimization suggestions"""
    try:
        from app.engine.universal_service_cache import get_service_cache_manager
        
        service_cache = get_service_cache_manager()
        stats = service_cache.get_cache_statistics()
        
        memory_ratio = stats['memory_usage_mb'] / stats['max_memory_mb']
        
        click.echo(f"\n💾 CACHE MEMORY ANALYSIS")
        click.echo("="*60)
        click.echo(f"Current Usage: {stats['memory_usage_mb']:.1f}MB")
        click.echo(f"Memory Limit: {stats['max_memory_mb']:.0f}MB")
        click.echo(f"Usage Ratio: {memory_ratio:.1%}")
        click.echo(f"Available: {stats['max_memory_mb'] - stats['memory_usage_mb']:.1f}MB")
        
        # Memory Status Assessment
        if memory_ratio > 0.95:
            status = "🔴 CRITICAL"
            urgency = "IMMEDIATE ACTION REQUIRED"
        elif memory_ratio > threshold:
            status = "🟡 HIGH"
            urgency = "ATTENTION RECOMMENDED"
        elif memory_ratio > 0.50:
            status = "🟢 NORMAL"
            urgency = "OPTIMAL"
        else:
            status = "🔵 LOW"
            urgency = "UNDERUTILIZED"
        
        click.echo(f"\nMemory Status: {status} ({urgency})")
        
        # Detailed Analysis
        if detailed:
            click.echo(f"\n📊 DETAILED MEMORY BREAKDOWN:")
            
            # Entity-specific memory usage (if available)
            if 'entity_stats' in stats and stats['entity_stats']:
                click.echo(f"   Entity Memory Distribution:")
                total_hits = sum(entity_stats['hits'] for entity_stats in stats['entity_stats'].values())
                
                for entity, entity_stats in sorted(stats['entity_stats'].items(), 
                                                 key=lambda x: x[1]['hits'], reverse=True):
                    hit_percentage = (entity_stats['hits'] / total_hits * 100) if total_hits > 0 else 0
                    estimated_memory = (hit_percentage / 100) * stats['memory_usage_mb']
                    click.echo(f"     {entity:<15}: ~{estimated_memory:>5.1f}MB ({hit_percentage:>5.1f}% of requests)")
            
            # Cache efficiency metrics
            click.echo(f"\n⚡ EFFICIENCY METRICS:")
            click.echo(f"   Memory per Request: {(stats['memory_usage_mb'] * 1024) / max(1, stats['total_hits']):.2f}KB")
            click.echo(f"   Hits per MB: {stats['total_hits'] / max(1, stats['memory_usage_mb']):.0f}")
            click.echo(f"   Memory Turnover: {stats.get('cache_turnover_rate', 'N/A')}")
        
        # Recommendations
        click.echo(f"\n💡 OPTIMIZATION RECOMMENDATIONS:")
        
        if memory_ratio > 0.95:
            click.echo(f"   🚨 CRITICAL - Run immediately:")
            click.echo(f"     1. flask cache clear  # Emergency cache clear")
            click.echo(f"     2. Increase SERVICE_CACHE_MAX_MEMORY_MB in .env")
            click.echo(f"     3. Run flask cache cleanup --min-age 1800  # Clean old entries")
        elif memory_ratio > threshold:
            click.echo(f"   ⚠️  RECOMMENDED ACTIONS:")
            click.echo(f"     1. flask cache cleanup --min-age 3600  # Clean entries older than 1h")
            click.echo(f"     2. Consider increasing SERVICE_CACHE_MAX_MEMORY_MB to {int(stats['max_memory_mb'] * 1.5)}MB")
            click.echo(f"     3. Review entity-specific cache usage patterns")
        elif memory_ratio < 0.30:
            click.echo(f"   📈 OPTIMIZATION OPPORTUNITIES:")
            click.echo(f"     1. Memory is underutilized - could increase cache size")
            click.echo(f"     2. Consider longer TTL to improve hit ratios")
            click.echo(f"     3. Cache more entities for better performance")
        else:
            click.echo(f"   ✅ MEMORY USAGE OPTIMAL")
            click.echo(f"     Current usage is within ideal range (30-{threshold:.0%})")
        
        # Memory Growth Prediction (if historical data available)
        if stats.get('requests_per_minute', 0) > 0:
            projected_daily_requests = stats['requests_per_minute'] * 60 * 24
            memory_per_request = stats['memory_usage_mb'] / max(1, stats['total_hits'])
            projected_daily_memory = projected_daily_requests * memory_per_request
            
            click.echo(f"\n📈 GROWTH PROJECTIONS:")
            click.echo(f"   Daily Request Projection: {projected_daily_requests:,.0f}")
            click.echo(f"   Daily Memory Growth: ~{projected_daily_memory:.1f}MB")
            
            if projected_daily_memory > stats['max_memory_mb'] * 0.5:
                click.echo(f"   ⚠️  Consider increasing memory limit for sustained load")
        
        click.echo("="*60)
        
    except Exception as e:
        click.echo(f"❌ Memory analysis failed: {str(e)}")

@cache.command()
@click.option('--min-age', type=int, help='Clean entries older than N seconds')
@click.option('--entity-type', help='Clean specific entity type only')
@click.option('--dry-run', is_flag=True, help='Show what would be cleaned without doing it')
@with_appcontext
def cleanup(min_age, entity_type, dry_run):
    """Advanced cache cleanup with detailed analysis"""
    try:
        from app.engine.universal_service_cache import get_service_cache_manager
        
        service_cache = get_service_cache_manager()
        
        click.echo(f"\n🧹 CACHE CLEANUP ANALYSIS")
        click.echo("="*50)
        
        # Get current stats before cleanup
        before_stats = service_cache.get_cache_statistics()
        
        if dry_run:
            click.echo(f"🔍 DRY RUN MODE - No actual cleanup performed")
        
        # Perform cleanup based on options
        cleaned_count = 0
        
        if entity_type and min_age:
            if dry_run:
                # Simulate cleanup for analysis
                click.echo(f"Would clean {entity_type} entries older than {min_age}s")
            else:
                cleaned_count = service_cache.cleanup_old_entries(entity_type, min_age)
            click.echo(f"Target: {entity_type} entries older than {min_age}s")
            
        elif entity_type:
            if dry_run:
                click.echo(f"Would clean all {entity_type} cache entries")
            else:
                cleaned_count = service_cache.cleanup_entity_cache(entity_type)
            click.echo(f"Target: All {entity_type} entries")
            
        elif min_age:
            if dry_run:
                click.echo(f"Would clean all entries older than {min_age}s")
            else:
                cleaned_count = service_cache.cleanup_old_entries(min_age_seconds=min_age)
            click.echo(f"Target: All entries older than {min_age}s ({min_age//60}min)")
            
        else:
            # Standard cleanup of expired entries
            if dry_run:
                click.echo(f"Would clean expired entries")
            else:
                cleaned_count = service_cache.cleanup_expired_entries()
            click.echo(f"Target: Expired entries only")
        
        # Show results
        if not dry_run:
            # Get stats after cleanup
            after_stats = service_cache.get_cache_statistics()
            memory_freed = before_stats['memory_usage_mb'] - after_stats['memory_usage_mb']
            
            click.echo(f"\n📊 CLEANUP RESULTS:")
            click.echo(f"   Entries Removed: {cleaned_count}")
            click.echo(f"   Memory Freed: {memory_freed:.1f}MB")
            click.echo(f"   Before: {before_stats['memory_usage_mb']:.1f}MB")
            click.echo(f"   After: {after_stats['memory_usage_mb']:.1f}MB")
            
            # Performance impact analysis
            if cleaned_count > 0:
                impact_ratio = cleaned_count / max(1, before_stats['total_hits'] + before_stats['total_misses'])
                click.echo(f"\n⚡ PERFORMANCE IMPACT:")
                if impact_ratio < 0.10:
                    click.echo(f"   🟢 Low impact: {impact_ratio:.1%} of cache cleared")
                elif impact_ratio < 0.30:
                    click.echo(f"   🟡 Medium impact: {impact_ratio:.1%} of cache cleared")
                else:
                    click.echo(f"   🔴 High impact: {impact_ratio:.1%} of cache cleared")
                    click.echo(f"   💡 Consider warming cache: flask cache warm")
        else:
            # Dry run summary
            click.echo(f"\n📋 DRY RUN SUMMARY:")
            click.echo(f"   Run without --dry-run to execute cleanup")
            click.echo(f"   Current memory usage: {before_stats['memory_usage_mb']:.1f}MB")
        
        click.echo("="*50)
        
    except Exception as e:
        click.echo(f"❌ Cleanup failed: {str(e)}")

@cache.command()
@click.option('--verbose', is_flag=True, help='Show detailed diagnostic information')
@click.option('--check-entities', is_flag=True, help='Check entity-specific performance')
@with_appcontext
def debug(verbose, check_entities):
    """Comprehensive cache debugging and diagnostics"""
    try:
        from app.engine.universal_service_cache import get_service_cache_manager
        from app.engine.universal_config_cache import get_cached_configuration_loader
        
        click.echo("\n🔍 UNIVERSAL ENGINE CACHE DIAGNOSTICS")
        click.echo("="*65)
        
        # System Status
        service_cache = get_service_cache_manager()
        config_cache = get_cached_configuration_loader()
        
        service_stats = service_cache.get_cache_statistics()
        config_stats = config_cache.get_cache_statistics()
        
        click.echo(f"🏥 SYSTEM STATUS:")
        click.echo(f"   Service Cache: {'✅ Active' if service_cache else '❌ Not Available'}")
        click.echo(f"   Config Cache: {'✅ Active' if config_cache else '❌ Not Available'}")
        click.echo(f"   Uptime: {service_stats.get('uptime_hours', 0):.1f} hours")
        
        # Configuration Validation
        click.echo(f"\n⚙️  CONFIGURATION VALIDATION:")
        config_checks = [
            ('SERVICE_CACHE_ENABLED', current_app.config.get('SERVICE_CACHE_ENABLED')),
            ('CONFIG_CACHE_ENABLED', current_app.config.get('CONFIG_CACHE_ENABLED')),
            ('CACHE_MONITORING_ENABLED', current_app.config.get('CACHE_MONITORING_ENABLED'))
        ]
        
        for key, value in config_checks:
            status = '✅' if value else '❌'
            source = '🌐' if os.getenv(key) else '⚙️'
            click.echo(f"   {status} {source} {key}: {value}")
        
        # Performance Analysis
        overall_performance = (service_stats['hit_ratio'] + config_stats['hit_ratio']) / 2
        click.echo(f"\n📊 PERFORMANCE ANALYSIS:")
        click.echo(f"   Overall Hit Ratio: {overall_performance:.2%}")
        click.echo(f"   Performance Grade: {_calculate_performance_grade(service_stats, config_stats)}")
        
        # Entity-Specific Analysis
        if check_entities and 'entity_stats' in service_stats:
            click.echo(f"\n🎯 ENTITY-SPECIFIC ANALYSIS:")
            
            best_entities = []
            worst_entities = []
            
            for entity, entity_stats in service_stats['entity_stats'].items():
                hit_ratio = entity_stats.get('hit_ratio', 0)
                if hit_ratio > 0.90:
                    best_entities.append((entity, hit_ratio))
                elif hit_ratio < 0.70:
                    worst_entities.append((entity, hit_ratio))
            
            if best_entities:
                click.echo(f"   🏆 TOP PERFORMERS:")
                for entity, ratio in sorted(best_entities, key=lambda x: x[1], reverse=True)[:5]:
                    click.echo(f"     {entity:<15}: {ratio:.1%}")
            
            if worst_entities:
                click.echo(f"   ⚠️  NEEDS ATTENTION:")
                for entity, ratio in sorted(worst_entities, key=lambda x: x[1])[:5]:
                    click.echo(f"     {entity:<15}: {ratio:.1%}")
        
        # Detailed Cache Contents (if verbose)
        if verbose:
            click.echo(f"\n🔍 DETAILED DIAGNOSTICS:")
            
            # Show cache keys (first 10)
            if hasattr(service_cache, 'get_all_cache_keys'):
                cache_keys = service_cache.get_all_cache_keys()
                click.echo(f"   Total Cache Keys: {len(cache_keys)}")
                if cache_keys:
                    click.echo(f"   Sample Keys (first 10):")
                    for key in sorted(cache_keys)[:10]:
                        click.echo(f"     {key}")
                    if len(cache_keys) > 10:
                        click.echo(f"     ... and {len(cache_keys) - 10} more")
            
            # Environment Variables Audit
            click.echo(f"\n🌐 ENVIRONMENT VARIABLES:")
            cache_env_vars = [k for k in os.environ.keys() if 'CACHE' in k.upper()]
            if cache_env_vars:
                for var in sorted(cache_env_vars):
                    click.echo(f"     {var}: {os.environ[var]}")
            else:
                click.echo(f"     No cache-related environment variables found")
        
        # Optimization Recommendations
        recommendations = _generate_performance_recommendations(service_stats, config_stats)
        if recommendations:
            click.echo(f"\n💡 OPTIMIZATION RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                click.echo(f"   {i}. {rec}")
        
        click.echo("="*65)
        
    except Exception as e:
        click.echo(f"❌ Debug analysis failed: {str(e)}")

@cache.command()
@click.option('--dashboard', is_flag=True, help='Start interactive dashboard mode')
@click.option('--duration', type=int, help='Monitor for N minutes then exit')
@with_appcontext
def monitor(dashboard, duration):
    """Advanced monitoring with interactive dashboard"""
    
    try:
        if dashboard:
            # Interactive Dashboard Mode
            click.echo(f"🎛️  INTERACTIVE CACHE DASHBOARD")
            click.echo("="*70)
            click.echo("Commands: [s]tats, [h]ealth, [c]lear, [w]arm, [e]xport, [q]uit")
            click.echo("="*70)
            
            try:
                while True:
                    # Show current status
                    from app.engine.universal_service_cache import get_service_cache_manager
                    service_cache = get_service_cache_manager()
                    stats = service_cache.get_cache_statistics()
                    
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    click.echo(f"\n[{timestamp}] Hit Ratio: {stats['hit_ratio']:.1%} | "
                              f"Memory: {stats['memory_usage_mb']:.1f}MB | "
                              f"Requests: {stats.get('requests_per_minute', 0):.1f}/min")
                    
                    # Interactive prompt
                    choice = click.prompt("Choose action", type=str, default='s').lower()
                    
                    if choice == 'q':
                        break
                    elif choice == 's':
                        os.system(f"python -m flask --app {__file__} cache stats")
                    elif choice == 'h':
                        os.system(f"python -m flask --app {__file__} cache health")
                    elif choice == 'c':
                        if click.confirm("Clear all caches?"):
                            os.system(f"python -m flask --app {__file__} cache clear")
                    elif choice == 'w':
                        os.system(f"python -m flask --app {__file__} cache warm")
                    elif choice == 'e':
                        os.system(f"python -m flask --app {__file__} cache export-stats --format detailed")
                    else:
                        click.echo("Invalid choice. Use s/h/c/w/e/q")
                        
            except KeyboardInterrupt:
                pass
            
            click.echo("\n✅ Interactive dashboard closed")
            
        else:
            # Standard monitoring with optional duration
            if duration:
                click.echo(f"📊 Monitoring for {duration} minutes...")
                
                start_time = datetime.now()
                end_time = start_time + timedelta(minutes=duration)
                
                performance_snapshots = []
                
                while datetime.now() < end_time:
                    from app.engine.universal_service_cache import get_service_cache_manager
                    service_cache = get_service_cache_manager()
                    stats = service_cache.get_cache_statistics()
                    
                    performance_snapshots.append({
                        'timestamp': datetime.now(),
                        'hit_ratio': stats['hit_ratio'],
                        'memory_usage': stats['memory_usage_mb'],
                        'requests_per_min': stats.get('requests_per_minute', 0)
                    })
                    
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    remaining = (end_time - datetime.now()).total_seconds() / 60
                    click.echo(f"[{timestamp}] Monitoring... {remaining:.1f}min remaining | "
                              f"Hit: {stats['hit_ratio']:.1%} | "
                              f"Mem: {stats['memory_usage_mb']:.1f}MB")
                    
                    time.sleep(30)  # 30 second intervals for duration monitoring
                
                # Duration monitoring summary
                if len(performance_snapshots) > 1:
                    avg_hit_ratio = sum(s['hit_ratio'] for s in performance_snapshots) / len(performance_snapshots)
                    avg_memory = sum(s['memory_usage'] for s in performance_snapshots) / len(performance_snapshots)
                    
                    click.echo(f"\n📊 {duration}-MINUTE MONITORING SUMMARY:")
                    click.echo(f"   Average Hit Ratio: {avg_hit_ratio:.2%}")
                    click.echo(f"   Average Memory: {avg_memory:.1f}MB")
                    click.echo(f"   Snapshots Taken: {len(performance_snapshots)}")
                    
                    # Export summary
                    summary_file = f"cache_monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(summary_file, 'w') as f:
                        json.dump({
                            'monitoring_session': {
                                'duration_minutes': duration,
                                'snapshots': performance_snapshots
                            }
                        }, f, indent=2, default=str)
                    click.echo(f"   📄 Summary exported: {summary_file}")
            
            else:
                click.echo("💡 Use --dashboard for interactive mode or --duration N for timed monitoring")
        
    except Exception as e:
        click.echo(f"❌ Monitoring failed: {str(e)}")

# ============================================================================
# REGISTER CLI COMMANDS
# ============================================================================

app.cli.add_command(cache)

# ============================================================================
# CONFIGURATION HELP & DOCUMENTATION
# ============================================================================

if __name__ == '__main__':
    print("🚀 Universal Engine Cache CLI - FULL FEATURED")
    print(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    
    print(f"\n⚙️  Cache Configuration:")
    print(f"  Service Cache: {'✅ Enabled' if CacheConfig.get_setting('SERVICE_CACHE_ENABLED') else '❌ Disabled'}")
    print(f"  Config Cache: {'✅ Enabled' if CacheConfig.get_setting('CONFIG_CACHE_ENABLED') else '❌ Disabled'}")
    print(f"  Memory Limit: {CacheConfig.get_setting('SERVICE_CACHE_MAX_MEMORY_MB')}MB")
    print(f"  Monitoring: {'✅ Enabled' if CacheConfig.get_setting('CACHE_MONITORING_ENABLED') else '❌ Disabled'}")
    
    print(f"\n🔧 BASIC COMMANDS:")
    print(f"  flask cache config             # View current configuration")
    print(f"  flask cache stats              # Comprehensive performance dashboard")
    print(f"  flask cache health             # System health check")
    print(f"  flask cache clear              # Clear all caches")
    print(f"  flask cache warm               # Warm up caches")
    print(f"  flask cache invalidate <entity> # Invalidate specific entity")
    
    print(f"\n📊 ADVANCED DASHBOARD COMMANDS:")
    print(f"  flask cache live               # Enhanced live dashboard with trending")
    print(f"  flask cache monitor --dashboard # Interactive dashboard mode")
    print(f"  flask cache monitor --duration 30 # Monitor for 30 minutes with summary")
    
    print(f"\n🔍 ANALYSIS & DIAGNOSTICS:")
    print(f"  flask cache memory-analysis    # Advanced memory analysis")
    print(f"  flask cache debug --verbose    # Detailed diagnostics")
    print(f"  flask cache cleanup --dry-run  # Analyze cleanup without executing")
    
    print(f"\n📄 EXPORT & REPORTING:")
    print(f"  flask cache export-stats --format detailed # Comprehensive analysis export")
    print(f"  flask cache export-stats --format csv     # Spreadsheet-friendly export")
    print(f"  flask cache export-stats --include-history # With historical data")
    
    print(f"\n💡 FULL FEATURE SET INCLUDES:")
    print(f"  ✅ Real-time dashboard with entity tracking")
    print(f"  ✅ Performance grading and recommendations")
    print(f"  ✅ Historical trend analysis")
    print(f"  ✅ Memory optimization analysis")
    print(f"  ✅ Interactive monitoring modes")
    print(f"  ✅ Advanced export capabilities")
    print(f"  ✅ Smart built-in configuration defaults")
    
    print(f"\n📝 Minimal .env Setup (only add what you want to override):")
    print(f"  SERVICE_CACHE_MAX_MEMORY_MB=1000  # Increase memory limit")
    print(f"  CACHE_LIVE_REFRESH_SECONDS=3      # Faster dashboard updates")