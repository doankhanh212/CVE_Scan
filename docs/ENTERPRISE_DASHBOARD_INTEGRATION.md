# CVE_Scan Enterprise Dashboard - Quick Integration Guide

## 🚀 5-Minute Setup

### Option 1: Use HTML Template (Easiest)

1. **Replace existing dashboard.html**
   ```bash
   cp web/templates/dashboard_enterprise.html web/templates/dashboard.html
   ```

2. **Update Flask route** (`web/routes/dashboard.py`):
   ```python
   from flask import Blueprint, render_template
   from web.services.scan_service import get_scan_stats, get_critical_alerts
   
   dashboard_bp = Blueprint('dashboard', __name__)
   
   @dashboard_bp.route('/')
   def dashboard():
       stats = get_scan_stats()
       severity = stats.get('severity', {
           'critical': 0,
           'high': 0,
           'medium': 0,
           'low': 0
       })
       
       return render_template('dashboard_enterprise.html',
           stats=stats,
           severity=severity,
           last_scan_time='Just now'
       )
   ```

3. **Ensure Chart.js is available** in `base.html`:
   ```html
   <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1"></script>
   ```

### Option 2: Use React Components

1. **Install dependencies** (if not already installed):
   ```bash
   npm install react chart.js react-chartjs-2
   ```

2. **Create dashboard route** (`web/routes/dashboard.py`):
   ```python
   @dashboard_bp.route('/api/dashboard-data')
   def dashboard_data():
       from flask import jsonify
       stats = get_scan_stats()
       alerts = get_critical_alerts(limit=3)
       
       return jsonify({
           'stats': stats,
           'alerts': alerts
       })
   ```

3. **Import and use component** in your React app:
   ```jsx
   import SecurityDashboard from './components/SecurityDashboard';
   
   export default function App() {
       return <SecurityDashboard />;
   }
   ```

---

## 📊 Data Format Reference

Your `get_scan_stats()` should return:

```python
def get_scan_stats():
    return {
        # KPI metrics
        'total_cves': 1247,          # Total CVEs found
        'critical': 42,               # Critical severity count
        'hosts_scanned': 156,         # Number of hosts
        'security_posture': 72,       # % score 0-100
        
        # Change indicators
        'cve_change': 127,            # New CVEs this period
        'critical_change': 8,         # New critical CVEs
        'hosts_change': 24,           # Newly scanned hosts
        'posture_change': 3,          # % point improvement
        
        # Severity breakdown
        'severity': {
            'critical': 42,           # CVSS 9.0-10.0
            'high': 156,              # CVSS 7.0-8.9
            'medium': 485,            # CVSS 4.0-6.9
            'low': 564                # CVSS 0.1-3.9
        },
        
        'last_scan_time': '2 minutes ago'
    }
```

Your `get_critical_alerts()` should return:

```python
def get_critical_alerts(limit=3):
    return [
        {
            'cve_id': 'CVE-2024-1234',
            'title': 'OpenSSH RCE',
            'description': 'Remote code execution in OpenSSH versions < 8.0',
            'hosts': '12',            # String with count
            'port': 'Port 22 (SSH)',  # Port/service name
            'severity': 'critical',   # One of: critical, high, medium, low
            'time_ago': '2 hours ago' # Human-readable time
        },
        # ... more alerts
    ]
```

---

## 🎨 Styling Integration

### Option 1: Include CSS Files Directly
```html
<!-- In base.html template -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/enterprise-dashboard.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/dashboard-panels.css') }}">
```

### Option 2: Use CSS Modules (React)
```jsx
import styles from '../styles/enterprise-dashboard.module.css';

// Components already import their styles
```

### Option 3: Tailwind CSS Version (Alternative)
```html
<!-- If using Tailwind CSS -->
<script src="https://cdn.tailwindcss.com"></script>
```

---

## 📱 Responsive Behavior

The dashboard automatically adapts to screen sizes:

| Screen Size | Layout |
|---|---|
| **Desktop** (1200px+) | Sidebar + 4-column KPI + 2×2 charts |
| **Tablet** (768px-1200px) | Collapsed sidebar + 2-column KPI + stacked charts |
| **Mobile** (<768px) | No sidebar + 1-column layout |

No additional code needed - it's built into the CSS!

---

## 🔌 API Endpoint Examples

### Get Dashboard Stats
```python
@app.route('/api/dashboard/stats')
def get_dashboard_stats():
    from web.services.scan_service import aggregate_scan_data
    
    data = aggregate_scan_data()
    return jsonify({
        'total_cves': data['cve_count'],
        'critical': len([c for c in data['cves'] if c['severity'] == 'CRITICAL']),
        # ... format as needed
    })
```

### Get Recent Vulnerabilities
```python
@app.route('/api/dashboard/vulnerabilities')
def get_vulnerabilities():
    from web.services.scan_service import get_recent_cves
    
    cves = get_recent_cves(limit=10)
    return jsonify({
        'vulnerabilities': cves
    })
```

### Get Chart Data
```python
@app.route('/api/dashboard/chart-data')
def get_chart_data():
    from web.services.scan_service import get_cve_trends
    
    trends = get_cve_trends(days=7)
    return jsonify({
        'trend_data': trends,
        'severity_distribution': {
            'critical': 42,
            'high': 156,
            'medium': 485,
            'low': 564
        }
    })
```

---

## 🎯 Common Customizations

### Change Color Scheme
Edit CSS variables at the top of each CSS file:

```css
:root {
    --color-critical: #ff0000;  /* Change red */
    --color-high: #ff6600;      /* Change orange */
    --color-medium: #ffcc00;    /* Change yellow */
    --color-low: #0066ff;       /* Change blue */
    
    --primary-bg: #000000;      /* Change background */
    --text-primary: #ffffff;    /* Change text */
}
```

### Add New KPI Card
```jsx
// In SecurityDashboard.jsx
<KPICard
    label="Patches Available"
    value={328}
    icon="📦"
    change="+45 this week"
    trend="positive"
    color="green"
/>
```

### Customize Alert Items
Edit the alert data structure and pass custom fields:

```jsx
const customAlerts = [
    {
        cveId: 'CVE-2024-1234',
        title: 'Your Custom Title',
        // ... other fields
        customField: 'custom value'
    }
];

<AlertPanel
    alerts={customAlerts}
    title="Custom Alerts"
/>
```

---

## ✅ Testing Checklist

- [ ] Dashboard loads without console errors
- [ ] Charts render properly
- [ ] Responsive layout works on mobile (test with DevTools)
- [ ] All KPI numbers display correctly
- [ ] Alert items show with proper colors
- [ ] Table is searchable
- [ ] Hover effects work on cards
- [ ] Status indicator pulses in header
- [ ] Last updated time is current

---

## 🐛 Troubleshooting

### Charts Not Rendering
```javascript
// Check if Chart.js is loaded
console.log(typeof Chart);  // Should be 'function'

// Ensure canvas elements exist
document.getElementById('severityChart');  // Should exist
```

### Styling Issues
```css
/* Check that CSS files are loaded */
// Open DevTools → Elements → check <head> for <link> tags

/* Clear browser cache */
// Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
```

### Data Not Displaying
```python
# Print stats object to verify data
import json
print(json.dumps(stats, indent=2))

# Check that all required fields are present
assert 'total_cves' in stats
assert 'severity' in stats
```

### Responsive Layout Not Working
```css
/* Ensure viewport meta tag exists */
<meta name="viewport" content="width=device-width, initial-scale=1.0">
```

---

## 🚀 Advanced: Real-time Updates

To add WebSocket support for live data updates:

```python
# In Flask with Flask-SocketIO
from flask_socketio import emit, SocketIO

socketio = SocketIO(app)

@socketio.on('connect')
def handle_connect():
    emit('dashboard_data', get_dashboard_stats())
```

```javascript
// In JavaScript/React
const socket = io();

socket.on('dashboard_data', (data) => {
    updateDashboard(data);
});

// Emit update request every 30 seconds
setInterval(() => {
    socket.emit('request_update');
}, 30000);
```

---

## 📈 Performance Tips

1. **Debounce table search**: Avoid updating on every keystroke
   ```jsx
   const [search, setSearch] = useState('');
   const debouncedSearch = useDebounce(search, 300);
   ```

2. **Lazy load charts**: Only render when visible
   ```jsx
   const [isVisible, setIsVisible] = useState(false);
   // Use Intersection Observer
   ```

3. **Cache API responses**: Don't fetch stats on every render
   ```jsx
   const { data: stats } = useSWR('/api/dashboard/stats', fetcher);
   ```

4. **Compress images/icons**: Use SVG or optimized PNG

---

## 📚 File Structure

```
web/
├── templates/
│   └── dashboard_enterprise.html    ← Main HTML template
├── components/
│   ├── EnterpriseLayout.jsx         ← Layout wrapper
│   ├── DashboardPanels.jsx          ← Panel components
│   ├── SecurityDashboard.jsx        ← Main component
│   └── Charts.jsx                   ← Chart components
├── styles/
│   ├── enterprise-dashboard.module.css
│   ├── dashboard-panels.module.css
│   └── security-dashboard.module.css
└── routes/
    └── dashboard.py                 ← Backend routes
```

---

## 🎓 Resources

- **Chart.js Docs**: https://www.chartjs.org/docs/latest/
- **CSS Variables**: https://developer.mozilla.org/en-US/docs/Web/CSS/--*
- **React Best Practices**: https://react.dev/learn
- **Responsive Design**: https://web.dev/responsive-web-design-basics/

---

## ❓ FAQ

**Q: Can I use this with Vue.js instead of React?**
A: Yes! The CSS and HTML are framework-agnostic. You'll need to port the React JSX to Vue templates, but the styling remains the same.

**Q: How do I add custom metrics to KPI cards?**
A: Edit the `KPICard` component props or create a new component extending it.

**Q: What if my data structure is different?**
A: Map your data in the route before passing to the template:
```python
formatted_stats = {
    'total_cves': your_data['cve_count'],
    'critical': your_data['severity_counts']['critical'],
    # ... transform as needed
}
```

**Q: Can I embed this in an existing dashboard?**
A: Yes! Use the individual components as building blocks or include the full SecurityDashboard component.

**Q: How often should data refresh?**
A: Currently set to manual refresh. Add polling or WebSocket for real-time updates.

---

## 📞 Getting Help

1. Check the ENTERPRISE_DASHBOARD_DESIGN_GUIDE.md for detailed documentation
2. Review component prop definitions in source files
3. Check browser console for JavaScript errors
4. Verify Flask routes are returning correct data format
5. Use browser DevTools to inspect element styling

