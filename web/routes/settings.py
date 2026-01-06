"""Settings route for managing application configuration."""

from flask import Blueprint, render_template, request, jsonify
from modules.config_manager import ConfigManager

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings", methods=["GET"])
def settings_page():
    """Render settings page."""
    return render_template("settings.html")


@settings_bp.route("/api/settings", methods=["GET"])
def get_settings():
    """Get current settings."""
    try:
        config = ConfigManager.load()
        
        # Don't send API key in plaintext to frontend
        settings = {
            "nvd_api_key": "***" if config.get("nvd_api_key") else "",
            "use_local_db": config.get("use_local_db", True),
            "local_db_path": config.get("local_db_path", "modules/cve/nvd_cve.db"),
            "log_verbosity": config.get("log_verbosity", "info"),
            "max_concurrent_scans": config.get("max_concurrent_scans", 2),
            "scan_timeout": config.get("scan_timeout", 60),
            "nmap_threads": config.get("nmap_threads", 10),
            "cve_cap_per_service": config.get("cve_cap_per_service", 100),
            "fuzzy_match_cpe": config.get("fuzzy_match_cpe", True),
            "fuzzy_match_threshold": config.get("fuzzy_match_threshold", 80),
            "enable_scheduling": config.get("enable_scheduling", False),
            "enable_email_alerts": config.get("enable_email_alerts", False),
            "email_smtp_server": config.get("email_smtp_server", ""),
            "retention_days": config.get("retention_days", 90),
        }
        
        return jsonify({"settings": settings}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@settings_bp.route("/api/settings", methods=["POST"])
def save_settings():
    """Save settings."""
    try:
        data = request.get_json() or {}
        
        # Load existing config
        config = ConfigManager.load()
        
        # Update with new values (skip API key if it's masked)
        if data.get("nvd_api_key") and data.get("nvd_api_key") != "***":
            config["nvd_api_key"] = data["nvd_api_key"]
        
        if "use_local_db" in data:
            config["use_local_db"] = data["use_local_db"]
        if "local_db_path" in data:
            config["local_db_path"] = data["local_db_path"]
        if "log_verbosity" in data:
            config["log_verbosity"] = data["log_verbosity"]
        if "max_concurrent_scans" in data:
            config["max_concurrent_scans"] = int(data["max_concurrent_scans"])
        if "scan_timeout" in data:
            config["scan_timeout"] = int(data["scan_timeout"])
        if "nmap_threads" in data:
            config["nmap_threads"] = int(data["nmap_threads"])
        if "cve_cap_per_service" in data:
            config["cve_cap_per_service"] = int(data["cve_cap_per_service"])
        if "fuzzy_match_cpe" in data:
            config["fuzzy_match_cpe"] = data["fuzzy_match_cpe"]
        if "fuzzy_match_threshold" in data:
            config["fuzzy_match_threshold"] = int(data["fuzzy_match_threshold"])
        if "enable_scheduling" in data:
            config["enable_scheduling"] = data["enable_scheduling"]
        if "enable_email_alerts" in data:
            config["enable_email_alerts"] = data["enable_email_alerts"]
        if "email_smtp_server" in data:
            config["email_smtp_server"] = data["email_smtp_server"]
        if "retention_days" in data:
            config["retention_days"] = int(data["retention_days"])
        
        # Save config
        ConfigManager.save(config)
        
        return jsonify({"message": "✅ Settings saved! API key and config will be applied to new scans."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@settings_bp.route("/api/settings/test-api", methods=["POST"])
def test_api_key():
    """Test NVD API key connectivity."""
    try:
        data = request.get_json() or {}
        api_key = data.get("nvd_api_key")
        
        if not api_key:
            return jsonify({"error": "API key is required"}), 400
        
        # Test NVD API connection
        import requests
        
        # Use NVD API v2 (v1 is deprecated)
        url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        headers = {"apiKey": api_key}
        params = {"resultsPerPage": 1}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            return jsonify({
                "status": "success",
                "message": "API key is valid and working"
            }), 200
        elif response.status_code == 401:
            return jsonify({
                "status": "error",
                "message": "Invalid API key (401 Unauthorized)"
            }), 400
        elif response.status_code == 429:
            return jsonify({
                "status": "error",
                "message": "Rate limit exceeded. Please try again later."
            }), 429
        else:
            return jsonify({
                "status": "error",
                "message": f"NVD API returned status {response.status_code}"
            }), 400
    except requests.exceptions.Timeout:
        return jsonify({
            "status": "error",
            "message": "Connection timeout. Check your internet connection."
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@settings_bp.route("/api/settings/db-status", methods=["GET"])
def get_db_status():
    """Get database status information."""
    try:
        import os
        from datetime import datetime
        
        config = ConfigManager.load()
        db_path = config.get("local_db_path", "modules/cve/nvd_cve.db")
        
        status = {
            "status": "Unknown",
            "last_updated": "Never",
            "cve_count": 0,
            "db_size": 0
        }
        
        if os.path.exists(db_path):
            # Get file info
            stat_info = os.stat(db_path)
            status["db_size"] = round(stat_info.st_size / (1024 * 1024), 2)  # MB
            
            # Get modification time
            mod_time = datetime.fromtimestamp(stat_info.st_mtime)
            status["last_updated"] = mod_time.strftime("%Y-%m-%d %H:%M:%S")
            status["status"] = "OK"
            
            # Try to count CVEs in database
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM cves")
                status["cve_count"] = cursor.fetchone()[0]
                conn.close()
            except:
                status["cve_count"] = 0
        else:
            status["status"] = "Not Found"
        
        return jsonify(status), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@settings_bp.route("/api/settings/rebuild-db", methods=["POST"])
def rebuild_db():
    """Rebuild local CVE database from feeds."""
    try:
        import os
        import threading
        from modules.cve.db_importer import import_feeds
        
        config = ConfigManager.load()
        db_path = config.get("local_db_path", "modules/cve/nvd_cve.db")
        feed_dir = config.get("feed_dir", "modules/cve/nvd_data")
        
        # Check if feed directory exists
        if not os.path.exists(feed_dir):
            return jsonify({
                "error": "Feed directory not found. Please download feeds first.",
                "feed_dir": feed_dir
            }), 400
        
        # Run rebuild in background thread
        def rebuild_task():
            try:
                print(f"[INFO] Starting database rebuild from {feed_dir}")
                
                # Remove old database to force fresh rebuild
                if os.path.exists(db_path):
                    os.remove(db_path)
                    print(f"[INFO] Removed old database: {db_path}")
                
                # Import feeds
                import_feeds(feed_dir, db_path)
                
                # Touch the file to update modification time
                os.utime(db_path, None)
                
                print(f"[INFO] Database rebuild completed successfully")
            except Exception as e:
                print(f"[ERROR] Database rebuild failed: {e}")
        
        # Start background thread
        thread = threading.Thread(target=rebuild_task, daemon=True)
        thread.start()
        
        return jsonify({
            "message": "Database rebuild started in background",
            "status": "processing",
            "db_path": db_path
        }), 202
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@settings_bp.route("/api/settings/export", methods=["GET"])
def export_settings():
    """Export settings to JSON file."""
    try:
        import json
        from flask import make_response
        
        config = ConfigManager.load()
        
        # Remove sensitive data
        if "nvd_api_key" in config:
            config["nvd_api_key"] = "***MASKED***"
        
        response = make_response(json.dumps(config, indent=2))
        response.headers["Content-Disposition"] = "attachment; filename=cve_scan_settings.json"
        response.headers["Content-Type"] = "application/json"
        
        return response, 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@settings_bp.route("/api/settings/reset", methods=["POST"])
def reset_settings():
    """Reset settings to defaults."""
    try:
        DEFAULT_CONFIG = {
            "nvd_api_key": "",
            "use_local_db": True,
            "local_db_path": "modules/cve/nvd_cve.db",
            "log_verbosity": "info",
            "max_concurrent_scans": 2,
            "scan_timeout": 60,
            "nmap_threads": 10,
            "cve_cap_per_service": 100,
            "fuzzy_match_cpe": True,
            "fuzzy_match_threshold": 80,
            "enable_scheduling": False,
            "enable_email_alerts": False,
            "email_smtp_server": "",
            "retention_days": 90,
        }
        
        ConfigManager.save(DEFAULT_CONFIG)
        
        return jsonify({
            "message": "Settings reset to defaults successfully"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
