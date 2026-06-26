import json
import os
import sys
import logging
from mcp.server.fastmcp import FastMCP

# Setup logging to stderr because print to stdout corrupts stdio protocol
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("aquaguard_mcp")

mcp = FastMCP("aquaguard_mcp", description="AquaGuard Environmental Tools")

HOTSPOTS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hotspots.json")
VOLUNTEERS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "volunteers.json")

@mcp.tool()
def get_water_standards() -> str:
    """Get the standard EPA safety limits for water quality contaminants.
    
    Returns:
        A JSON string of water safety standard thresholds.
    """
    logger.info("Fetching water standards.")
    standards = {
        "lead": "max 0.015 mg/L",
        "ph": "6.5 to 8.5",
        "turbidity": "max 5.0 NTU",
        "chlorine": "max 4.0 mg/L",
        "arsenic": "max 0.010 mg/L"
    }
    return json.dumps(standards)

@mcp.tool()
def log_hotspot(location: str, issue: str, severity: str) -> str:
    """Log a confirmed water contamination hotspot to the community map.
    
    Args:
        location: The street name, neighborhood, or coordinates of the hotspot.
        issue: Brief description of the contaminant or issue (e.g. 'Lead', 'Turbid Water').
        severity: Severity rating ('Low', 'Medium', 'High').
        
    Returns:
        A confirmation message indicating successful logging.
    """
    logger.info(f"Logging hotspot at {location}")
    hotspots = []
    if os.path.exists(HOTSPOTS_FILE):
        try:
            with open(HOTSPOTS_FILE, "r") as f:
                hotspots = json.load(f)
        except Exception as e:
            logger.error(f"Error reading hotspots file: {e}")
            
    hotspots.append({
        "location": location,
        "issue": issue,
        "severity": severity,
        "status": "Logged"
    })
    
    try:
        with open(HOTSPOTS_FILE, "w") as f:
            json.dump(hotspots, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing hotspots: {e}")
        return f"Failed to log hotspot: {str(e)}"
        
    return f"Success: Hotspot logged at {location} (Issue: {issue}, Severity: {severity})."

@mcp.tool()
def register_volunteer(name: str, email: str, location: str) -> str:
    """Register a volunteer for clean-up or notification efforts in a specific area.
    
    Args:
        name: Name of the volunteer.
        email: Email address of the volunteer.
        location: Location where the volunteer wants to assist.
        
    Returns:
        A confirmation message indicating successful registration.
    """
    logger.info(f"Registering volunteer {name} for {location}")
    volunteers = []
    if os.path.exists(VOLUNTEERS_FILE):
        try:
            with open(VOLUNTEERS_FILE, "r") as f:
                volunteers = json.load(f)
        except Exception as e:
            logger.error(f"Error reading volunteers file: {e}")
            
    volunteers.append({
        "name": name,
        "email": email,
        "location": location
    })
    
    try:
        with open(VOLUNTEERS_FILE, "w") as f:
            json.dump(volunteers, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing volunteers: {e}")
        return f"Failed to register volunteer: {str(e)}"
        
    return f"Success: Volunteer {name} registered for cleanup in {location}."

if __name__ == "__main__":
    mcp.run(transport="stdio")
