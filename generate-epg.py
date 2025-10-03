import requests
import json
from datetime import datetime, timedelta
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import pytz
import re

# ============================================================================
# CONFIGURATION - Edit these sections for your channels
# ============================================================================

# Channel ID Prefixes (to avoid conflicts between sources)
PREFIX_DISTRO = "DS"
PREFIX_KABLEONE = "KO"
PREFIX_STIRR = "ST"

# Distro TV Channels
DISTRO_CHANNEL_IDS = [
    141278,  # World Punjabi TV
    138742,  # Living India News
    66501,   # Garv Punjab Gurbani
    71637,   # TV Punjab
    135913,  # Punjabi Hits
    126109,  # Saga Music
    87417,   # Bollywood Classic
    87418,   # Bollywood HD
    126290,  # Zee BollyWorld
    135729,  # Willow Sports
    138922,  # Sports First TV
    79275,   # beIN SPORTS Xtra
    77840,   # Boxing TV
    136902,  # SportsTVPlus
    78918    # TNA Wrestling Channel
]

# KableOne Channels
KABLEONE_CHANNEL_HANDLES = [
    'Chardikla-Time-Tv-North-America',
    'Chardikla-Time-TV',
    'Chardikla-Gurbani-TV'
]

# Stirr Channels
STIRR_CHANNEL_IDS = [
    5294  # Cricket Gold
]

# Output Configuration
OUTPUT_FILE = "epg.xml"
DISTRO_FETCH_DAYS = 3  # Number of days to fetch from Distro TV

# ============================================================================
# API ENDPOINTS
# ============================================================================

DISTRO_API_URL = "https://tv.jsrdn.com/epg/query.php"
KABLEONE_API_URL = "https://www.kableone.com/LiveTV/LoadTVChannelDetails"
STIRR_API_URL = "https://stirr.com/api/epg"

# Stirr requires browser headers to avoid 403 errors
STIRR_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://stirr.com/',
    'Origin': 'https://stirr.com'
}

# ============================================================================
# DISTRO TV
# ============================================================================

def fetch_distro_epg(channel_ids, days=3):
    """Fetch EPG data from Distro TV for multiple days"""
    print(f"\n{'='*60}")
    print(f"Fetching Distro TV EPG")
    print(f"{'='*60}")
    print(f"Channels: {len(channel_ids)}")
    print(f"Days: {days}\n")
    
    all_data = []
    
    for day in range(days):
        
        range_param ="now,72h"
        
        params = {
            'range': range_param,
            'id': ','.join(map(str, channel_ids))
        }
        
        try:
            response = requests.get(DISTRO_API_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            all_data.append(data)
            print(f"  ✅ Day {day + 1} fetched")
        except Exception as e:
            print(f"  ❌ Error fetching day {day + 1}: {e}")
    
    # Merge data
    merged = {}
    for data in all_data:
        if 'epg' not in data:
            continue
        for channel_id, channel_data in data['epg'].items():
            prefixed_id = f"{PREFIX_DISTRO}-{channel_id}"
            if prefixed_id not in merged:
                merged[prefixed_id] = {
                    'id': prefixed_id,
                    'original_id': channel_id,
                    'name': channel_data.get('title'),
                    'description': channel_data.get('description'),
                    'icon': None,
                    'programs': []
                }
            merged[prefixed_id]['programs'].extend(channel_data.get('slots', []))
    
    print(f"\n✅ Distro TV: {len(merged)} channels, {sum(len(ch['programs']) for ch in merged.values())} programmes")
    return list(merged.values())

# ============================================================================
# KABLEONE FUNCTIONS
# ============================================================================

def fetch_kableone_epg(channel_handles):
    """Fetch EPG data from KableOne"""
    print(f"\n{'='*60}")
    print(f"Fetching KableOne EPG")
    print(f"{'='*60}")
    print(f"Channels: {len(channel_handles)}\n")
    
    channels_data = []
    
    for handle in channel_handles:
        params = {'channelHandle': handle}
        
        try:
            print(f"  Fetching: {handle}")
            response = requests.get(KABLEONE_API_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if 'mediaDetails' not in data:
                print(f"    ⚠️ No data found")
                continue
            
            details = data['mediaDetails']
            channel_id = str(details.get('tvChannelId', ''))
            prefixed_id = f"{PREFIX_KABLEONE}-{channel_id}"
            
            channel_info = {
                'id': prefixed_id,
                'original_id': channel_id,
                'name': details.get('tvChannelName', 'Unknown'),
                'description': details.get('description'),
                'icon': details.get('tvChannelImage'),
                'programs': details.get('scheduledPrograms', [])
            }
            
            channels_data.append(channel_info)
            print(f"    ✅ {len(channel_info['programs'])} programmes")
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    print(f"\n✅ KableOne: {len(channels_data)} channels, {sum(len(ch['programs']) for ch in channels_data)} programmes")
    return channels_data

# ============================================================================
# STIRR
# ============================================================================

def fetch_stirr_epg(channel_ids):
    """Fetch EPG data from Stirr"""
    print(f"\n{'='*60}")
    print(f"Fetching Stirr EPG")
    print(f"{'='*60}")
    print(f"Channels: {len(channel_ids)}\n")
    
    channels_data = []
    
    for channel_id in channel_ids:
        params = {'channel_id': channel_id}
        
        try:
            print(f"  Fetching: {channel_id}")
            response = requests.get(STIRR_API_URL, params=params, headers=STIRR_HEADERS, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 200 or 'data' not in data:
                print(f"    ⚠️ No data found")
                continue
            
            channel_data = data['data']
            prefixed_id = f"{PREFIX_STIRR}-{channel_id}"
            
            channel_info = {
                'id': prefixed_id,
                'original_id': str(channel_id),
                'name': channel_data.get('name', 'Unknown'),
                'description': None,
                'icon': channel_data.get('icon') if channel_data.get('icon') != 'false' else None,
                'channel_number': channel_data.get('channel_number'),
                'programs': channel_data.get('programs', [])
            }
            
            channels_data.append(channel_info)
            print(f"    ✅ {len(channel_info['programs'])} programmes")
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    print(f"\n✅ Stirr: {len(channels_data)} channels, {sum(len(ch['programs']) for ch in channels_data)} programmes")
    return channels_data

# ============================================================================
# DATETIME PARSING FUNCTIONS
# ============================================================================

def parse_distro_datetime(dt_string):
    """Parse Distro TV datetime: 2025-09-30 06:26:00"""
    try:
        dt = datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
        dt = pytz.UTC.localize(dt)
        return dt
    except Exception as e:
        print(f"  ⚠️ Error parsing Distro datetime '{dt_string}': {e}")
        return None

def parse_kableone_datetime(dt_string):
    """Parse KableOne datetime: 2025-10-02T05:30:00"""
    try:
        dt = datetime.strptime(dt_string, '%Y-%m-%dT%H:%M:%S')
        dt = pytz.UTC.localize(dt)
        return dt
    except Exception as e:
        print(f"  ⚠️ Error parsing KableOne datetime '{dt_string}': {e}")
        return None

def parse_stirr_datetime(dt_string):
    """Parse Stirr datetime with timezone: 2025-09-29 23:27:53 -07:00"""
    try:
        if ' -' in dt_string or ' +' in dt_string:
            parts = dt_string.rsplit(' ', 1)
            dt_part = parts[0]
            tz_part = parts[1] if len(parts) > 1 else '+00:00'
            
            dt = datetime.strptime(dt_part, '%Y-%m-%d %H:%M:%S')
            
            tz_match = re.match(r'([+-])(\d{2}):(\d{2})', tz_part)
            if tz_match:
                sign = 1 if tz_match.group(1) == '+' else -1
                hours = int(tz_match.group(2))
                minutes = int(tz_match.group(3))
                
                dt = dt.replace(tzinfo=pytz.FixedOffset(sign * (hours * 60 + minutes)))
                dt = dt.astimezone(pytz.UTC)
            else:
                dt = pytz.UTC.localize(dt)
        else:
            dt = datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
            dt = pytz.UTC.localize(dt)
        
        return dt
    except Exception as e:
        print(f"  ⚠️ Error parsing Stirr datetime '{dt_string}': {e}")
        return None

# ============================================================================
# XMLTV GENERATION
# ============================================================================

def create_unified_xmltv(distro_channels, kableone_channels, stirr_channels):
    """Create unified XMLTV from all sources"""
    tv = Element('tv')
    tv.set('generator-info-name', 'EPG Generator')
    tv.set('generator-info-url', 'https://github.com/mdbass/extract-epg')
    
    all_channels = distro_channels + kableone_channels + stirr_channels
    
    # Add all channels
    for channel_info in all_channels:
        channel = SubElement(tv, 'channel')
        channel.set('id', channel_info['id'])
        
        display_name = SubElement(channel, 'display-name')
        display_name.text = channel_info['name']
        
        # Add channel number if available (Stirr)
        if channel_info.get('channel_number'):
            display_name_num = SubElement(channel, 'display-name')
            display_name_num.text = str(channel_info['channel_number'])
        
        if channel_info.get('description'):
            desc = SubElement(channel, 'desc')
            desc.set('lang', 'en')
            desc.text = channel_info['description']
        
        if channel_info.get('icon'):
            icon = SubElement(channel, 'icon')
            icon.set('src', channel_info['icon'])
    
    # Add programmes from Distro TV
    for channel_info in distro_channels:
        for program in channel_info['programs']:
            start_dt = parse_distro_datetime(program['start'])
            end_dt = parse_distro_datetime(program['end'])
            
            if not start_dt or not end_dt:
                continue
            
            programme = SubElement(tv, 'programme')
            programme.set('channel', channel_info['id'])
            programme.set('start', start_dt.strftime('%Y%m%d%H%M%S +0000'))
            programme.set('stop', end_dt.strftime('%Y%m%d%H%M%S +0000'))
            
            title = SubElement(programme, 'title')
            title.set('lang', 'en')
            title.text = program['title']
            
            if program.get('description'):
                desc = SubElement(programme, 'desc')
                desc.set('lang', 'en')
                desc.text = program['description']
    
    # Add programmes from KableOne
    for channel_info in kableone_channels:
        for program in channel_info['programs']:
            start_dt = parse_kableone_datetime(program['fromDate'])
            end_dt = parse_kableone_datetime(program['toDate'])
            
            if not start_dt or not end_dt:
                continue
            
            programme = SubElement(tv, 'programme')
            programme.set('channel', channel_info['id'])
            programme.set('start', start_dt.strftime('%Y%m%d%H%M%S +0000'))
            programme.set('stop', end_dt.strftime('%Y%m%d%H%M%S +0000'))
            
            title = SubElement(programme, 'title')
            title.set('lang', 'en')
            program_title = program.get('programmeName') or program.get('title') or 'Unknown Programme'
            title.text = ' '.join(program_title.split())
            
            if program.get('url'):
                icon = SubElement(programme, 'icon')
                icon.set('src', program['url'])
    
    # Add programmes from Stirr
    for channel_info in stirr_channels:
        for program in channel_info['programs']:
            start_dt_str = program.get('start_epg_time') or program.get('start')
            end_dt_str = program.get('end_epg_time') or program.get('end')
            
            start_dt = parse_stirr_datetime(start_dt_str)
            end_dt = parse_stirr_datetime(end_dt_str)
            
            if not start_dt or not end_dt:
                continue
            
            programme = SubElement(tv, 'programme')
            programme.set('channel', channel_info['id'])
            programme.set('start', start_dt.strftime('%Y%m%d%H%M%S +0000'))
            programme.set('stop', end_dt.strftime('%Y%m%d%H%M%S +0000'))
            
            title = SubElement(programme, 'title')
            title.set('lang', 'en')
            title.text = program.get('title', 'Unknown Programme')
            
            if program.get('description'):
                desc = SubElement(programme, 'desc')
                desc.set('lang', 'en')
                desc.text = program['description']
            
            if program.get('episode_number'):
                ep_info = program['episode_number']
                season = ep_info.get('season', 0)
                episode = ep_info.get('episode')
                
                if episode:
                    episode_num = SubElement(programme, 'episode-num')
                    episode_num.set('system', 'xmltv_ns')
                    episode_num.text = f"{season}.{int(episode) - 1 if episode else 0}.0/1"
            
            if program.get('date'):
                date_elem = SubElement(programme, 'date')
                date_elem.text = program['date']
    
    return tv

def prettify_xml(elem):
    """Return a pretty-printed XML string"""
    rough_string = tostring(elem, encoding='utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    print("\n" + "=" * 60)
    print("EPG GENERATOR")
    print("=" * 60)
    print(f"\nSources:")
    print(f"  • Distro TV: {len(DISTRO_CHANNEL_IDS)} channels")
    print(f"  • KableOne: {len(KABLEONE_CHANNEL_HANDLES)} channels")
    print(f"  • Stirr: {len(STIRR_CHANNEL_IDS)} channels")
    print(f"\nTotal channels: {len(DISTRO_CHANNEL_IDS) + len(KABLEONE_CHANNEL_HANDLES) + len(STIRR_CHANNEL_IDS)}")
    
    # Fetch from all sources
    distro_data = fetch_distro_epg(DISTRO_CHANNEL_IDS, DISTRO_FETCH_DAYS) if DISTRO_CHANNEL_IDS else []
    kableone_data = fetch_kableone_epg(KABLEONE_CHANNEL_HANDLES) if KABLEONE_CHANNEL_HANDLES else []
    stirr_data = fetch_stirr_epg(STIRR_CHANNEL_IDS) if STIRR_CHANNEL_IDS else []
    
    # Create unified XMLTV
    print(f"\n{'='*60}")
    print("Generating unified XMLTV file...")
    print(f"{'='*60}")
    
    xmltv_root = create_unified_xmltv(distro_data, kableone_data, stirr_data)
    
    # Save to file
    xml_string = prettify_xml(xmltv_root)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(xml_string)
    
    # Final summary
    total_channels = len(distro_data) + len(kableone_data) + len(stirr_data)
    total_programmes = (
        sum(len(ch['programs']) for ch in distro_data) +
        sum(len(ch['programs']) for ch in kableone_data) +
        sum(len(ch['programs']) for ch in stirr_data)
    )
    
    print("\n" + "=" * 60)
    print("EPG GENERATION COMPLETE!")
    print("=" * 60)
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Total channels: {total_channels}")
    print(f"Total programmes: {total_programmes}")
    print(f"\nBreakdown:")
    print(f"  • Distro TV: {len(distro_data)} channels, {sum(len(ch['programs']) for ch in distro_data)} programmes")
    print(f"  • KableOne: {len(kableone_data)} channels, {sum(len(ch['programs']) for ch in kableone_data)} programmes")
    print(f"  • Stirr: {len(stirr_data)} channels, {sum(len(ch['programs']) for ch in stirr_data)} programmes")
    print("=" * 60)

if __name__ == "__main__":
    main()