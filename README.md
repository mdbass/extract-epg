# EPG Generator

Automatically generates a XMLTV EPG file from multiple sources: Distro TV, KableOne, and Stirr.

## 📋 Channel ID Format

To prevent conflicts between sources with similar IDs, each source uses a unique prefix:

- **Distro TV**: `DS-141278`
- **KableOne**: `KO-32`
- **Stirr**: `ST-5294`


## 📊 Supported Sources

### Distro TV
- API: `https://tv.jsrdn.com/epg/query.php`
- Supports: Multiple channels in single request
- Data: 3 days of EPG

### KableOne
- API: `https://www.kableone.com/LiveTV/LoadTVChannelDetails`
- Supports: One channel per request
- Data: Scheduled programs

### Stirr
- API: `https://stirr.com/api/epg`
- Supports: One channel per request
- Data: Full program listings with episode info
