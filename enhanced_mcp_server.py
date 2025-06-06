# enhanced_mcp_server.py
import os
from dotenv import load_dotenv
import sys
from typing import Dict, Any, Optional, List
import asyncio

from mcp.server.fastmcp import FastMCP
import openfda_client

load_dotenv()

mcp_app = FastMCP(
    name="EnhancedMedicationInformationService",
    version="0.3.0",
    description="MCP server providing comprehensive medication info using openFDA with shortage data and analytics"
)

def get_medication_profile_logic(drug_identifier: str, identifier_type: str) -> Dict[str, Any]:
    """Get complete drug profile including label and shortage information"""
    # Get label information
    label_info = openfda_client.fetch_drug_label_info(drug_identifier, identifier_type=identifier_type)

    # Determine best search term for shortage lookup
    shortage_search_term = drug_identifier
    if label_info and not label_info.get("error") and "openfda" in label_info:
        generic_names = label_info["openfda"].get("generic_name")
        if generic_names and isinstance(generic_names, list) and len(generic_names) > 0:
            shortage_search_term = generic_names[0]

    # Get shortage information
    shortage_info = openfda_client.fetch_drug_shortage_info(shortage_search_term)

    # Parse label information
    parsed_label_info = {}
    if label_info and not label_info.get("error"):
        parsed_label_info = {
            "brand_name": label_info.get("openfda", {}).get("brand_name", []),
            "generic_name": label_info.get("openfda", {}).get("generic_name", []),
            "manufacturer_name": label_info.get("openfda", {}).get("manufacturer_name", []),
            "route": label_info.get("openfda", {}).get("route", []),
            "dosage_form": label_info.get("openfda", {}).get("dosage_form", []),
            "strength": label_info.get("openfda", {}).get("strength", []),
            "indications_and_usage": label_info.get("indications_and_usage", ["Not available"]),
            "adverse_reactions": label_info.get("adverse_reactions", ["Not available"]),
            "warnings_and_cautions": label_info.get("warnings_and_cautions", ["Not available"]),
            "dosage_and_administration": label_info.get("dosage_and_administration", ["Not available"]),
            "contraindications": label_info.get("contraindications", ["Not available"]),
            "drug_interactions": label_info.get("drug_interactions", ["Not available"]),
        }
    else:
        parsed_label_info["error"] = label_info.get("error", "Unknown label API error")

    # Build comprehensive profile
    profile = {
        "drug_identifier_requested": drug_identifier,
        "identifier_type_used": identifier_type,
        "shortage_search_term": shortage_search_term,
        "label_information": parsed_label_info,
        "shortage_information": shortage_info,
        "data_sources": {
            "label_data": "openFDA Drug Label API",
            "shortage_data": "openFDA Drug Shortages API"
        }
    }

    # Determine overall status
    has_label_error = "error" in parsed_label_info
    has_shortage_error = "error" in shortage_info
    has_shortage_data = "shortages" in shortage_info and len(shortage_info["shortages"]) > 0

    if has_label_error and has_shortage_error:
        profile["overall_status"] = "Failed to retrieve label and shortage information"
    elif has_label_error:
        if has_shortage_data:
            profile["overall_status"] = "Retrieved shortage data but failed to get label information"
        else:
            profile["overall_status"] = "No shortage found and failed to get label information"
    elif has_shortage_error:
        profile["overall_status"] = "Retrieved label information but shortage API error occurred"
    elif not label_info or not label_info.get("openfda"):
        if has_shortage_data:
            profile["overall_status"] = "Found shortage information but label data was minimal"
        else:
            profile["overall_status"] = "No shortage found and label data was minimal"
    else:
        if has_shortage_data:
            profile["overall_status"] = "SUCCESS: Retrieved complete drug profile with current shortage information"
        else:
            profile["overall_status"] = "SUCCESS: Retrieved complete drug profile - no current shortages found"
    
    return profile

@mcp_app.tool()
async def get_medication_profile(
    drug_identifier: str,
    identifier_type: str = "openfda.generic_name"
) -> Dict[str, Any]:
    """
    Get complete drug information including label and shortage status
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_medication_profile_logic, drug_identifier, identifier_type)

@mcp_app.tool()
async def search_drug_shortages(
    search_term: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search for drug shortages using openFDA database
    """
    loop = asyncio.get_event_loop()
    shortage_info = await loop.run_in_executor(None, openfda_client.fetch_drug_shortage_info, search_term)
    
    result = {
        "search_term": search_term,
        "shortage_data": shortage_info,
        "data_source": "openFDA Drug Shortages API",
        "note": "Data from openFDA endpoint with 1,900+ shortage records"
    }
    
    return result

@mcp_app.tool()
async def get_shortage_search_guidance(
    drug_name: str
) -> Dict[str, Any]:
    """
    Get search guidance and tips for finding drug shortage information
    """
    loop = asyncio.get_event_loop()
    openfda_results = await loop.run_in_executor(None, openfda_client.fetch_drug_shortage_info, drug_name)
    
    guidance = {
        "drug_name": drug_name,
        "openfda_results": openfda_results,
        "additional_search_strategies": {
            "recommended_queries": [
                f"{drug_name} shortage 2025",
                f"{drug_name} drug shortage current",
                f"{drug_name} supply shortage FDA",
                f"ASHP {drug_name} shortage"
            ],
            "authoritative_sources": {
                "ashp_database": {
                    "url": "https://www.ashp.org/drug-shortages/current-shortages",
                    "description": "American Society of Health-System Pharmacists shortage database",
                    "search_method": "Use site search or browse by drug name"
                },
                "fda_database": {
                    "url": "https://www.accessdata.fda.gov/scripts/drugshortages/",
                    "description": "Official FDA Drug Shortage Database",
                    "search_method": "Search by active ingredient or brand name"
                }
            }
        },
        "data_source": "Combined openFDA API and additional source guidance"
    }
    
    return guidance

@mcp_app.tool()
async def search_drug_recalls(
    search_term: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search for drug recalls using openFDA enforcement database
    """
    loop = asyncio.get_event_loop()
    recall_info = await loop.run_in_executor(None, openfda_client.search_drug_recalls, search_term)
    
    return {
        "search_term": search_term,
        "recall_data": recall_info,
        "data_source": "openFDA Drug Enforcement API",
        "note": "Data from functional openFDA endpoint"
    }

@mcp_app.tool()
async def get_drug_label_only(
    drug_identifier: str,
    identifier_type: str = "openfda.generic_name"
) -> Dict[str, Any]:
    """
    Get only FDA label information for a drug
    """
    loop = asyncio.get_event_loop()
    label_info = await loop.run_in_executor(None, openfda_client.fetch_drug_label_info, drug_identifier, identifier_type)
    
    return {
        "drug_identifier": drug_identifier,
        "identifier_type": identifier_type,
        "label_data": label_info,
        "data_source": "openFDA Drug Label API",
        "reliability": "High - this endpoint is working correctly"
    }

@mcp_app.tool()
async def analyze_drug_market_trends(
    drug_name: str,
    months_back: int = 12
) -> Dict[str, Any]:
    """
    Analyze drug shortage patterns and market trends
    """
    loop = asyncio.get_event_loop()
    trend_analysis = await loop.run_in_executor(None, openfda_client.analyze_drug_market_trends, drug_name, months_back)
    
    return {
        "drug_analyzed": drug_name,
        "analysis_period": f"{months_back} months",
        "trend_data": trend_analysis,
        "data_source": "openFDA Drug Shortages API - Historical Analysis",
        "analysis_type": "Market Trends and Risk Assessment"
    }

@mcp_app.tool()
async def batch_drug_analysis(
    drug_list: List[str],
    include_trends: bool = False
) -> Dict[str, Any]:
    """
    Analyze multiple drugs for shortages, recalls, and risk assessment
    """
    if len(drug_list) > 25:
        return {
            "error": "Batch size too large. Maximum 25 drugs per batch.",
            "recommendation": "Split drug list into smaller batches for optimal performance"
        }
    
    loop = asyncio.get_event_loop()
    batch_results = await loop.run_in_executor(None, openfda_client.batch_drug_analysis, drug_list, include_trends)
    
    return {
        "batch_analysis": batch_results,
        "data_source": "openFDA APIs - Comprehensive Batch Analysis",
        "analysis_type": "Formulary Risk Assessment",
        "note": f"Analyzed {len(drug_list)} drugs with trend analysis: {'enabled' if include_trends else 'disabled'}"
    }

if __name__ == "__main__":
    print("mcp server starting", file=sys.stderr)
    mcp_app.run(transport='stdio')