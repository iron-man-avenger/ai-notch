import requests
import base64
from typing import Dict, Any, Optional, List
from core.db import get_setting

class AzureDevOpsClient:
    def __init__(self, organization: Optional[str] = None, project: Optional[str] = None, pat: Optional[str] = None):
        self.org = organization or get_setting("azure_org", "")
        self.project = project or get_setting("azure_project", "")
        self.pat = pat or get_setting("azure_pat", "")
        self.work_item_type = get_setting("azure_item_type", "Task")

    def is_configured(self) -> bool:
        return bool(self.org and self.project and self.pat)

    def _get_headers(self) -> Dict[str, str]:
        auth_str = f":{self.pat}"
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        return {
            "Content-Type": "application/json-patch+json",
            "Authorization": f"Basic {b64_auth}"
        }

    def create_work_item(self, title: str, description: str = "", tags: Optional[List[str]] = None, work_item_type: Optional[str] = None) -> Dict[str, Any]:
        item_type = work_item_type or self.work_item_type or "Task"
        
        # If not configured, simulate successful creation for local preview/testing
        if not self.is_configured():
            import random
            simulated_id = random.randint(1000, 9999)
            return {
                "success": True,
                "is_simulated": True,
                "id": simulated_id,
                "title": title,
                "url": f"https://dev.azure.com/{self.org or 'DemoOrg'}/{self.project or 'DemoProject'}/_workitems/edit/{simulated_id}",
                "message": "Created in Local Mode (Configure your Azure DevOps Org & PAT in Settings to push directly to cloud)."
            }

        url = f"https://dev.azure.com/{self.org}/{self.project}/_apis/wit/workitems/${item_type}?api-version=7.1-preview.3"
        
        # Format description with HTML breaks
        formatted_desc = description.replace("\n", "<br/>")
        patch_operations = [
            {"op": "add", "path": "/fields/System.Title", "value": title},
            {"op": "add", "path": "/fields/System.Description", "value": formatted_desc}
        ]
        
        if tags:
            tag_string = "; ".join(tags)
            patch_operations.append({"op": "add", "path": "/fields/System.Tags", "value": tag_string})

        try:
            response = requests.post(url, json=patch_operations, headers=self._get_headers(), timeout=10)
            if response.status_code in [200, 201]:
                data = response.json()
                item_id = data.get("id")
                html_url = data.get("_links", {}).get("html", {}).get("href", "")
                return {
                    "success": True,
                    "is_simulated": False,
                    "id": item_id,
                    "title": title,
                    "url": html_url,
                    "message": f"Successfully created Work Item #{item_id} in Azure DevOps!"
                }
            else:
                return {
                    "success": False,
                    "error": f"Azure DevOps API returned {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
