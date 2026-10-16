"""Read-only Kubernetes resource lists for investigation scope selectors."""

from fastapi import APIRouter, Query

from app.kubernetes.kubectl_executor import kubectl_executor

router = APIRouter(tags=["resources"])


@router.get("/namespaces")
def list_namespaces(context: str | None = Query(default=None)):
    result = kubectl_executor.get_json("namespaces", context=context)
    if not result.success:
        return {"namespaces": [], "error": result.error}
    names = sorted(
        item.get("metadata", {}).get("name", "")
        for item in (result.parsed_json or {}).get("items", [])
        if item.get("metadata", {}).get("name")
    )
    return {"namespaces": names, "error": None}


@router.get("/namespaces/{namespace}/pods")
def list_pods(namespace: str, context: str | None = Query(default=None)):
    result = kubectl_executor.get_json("pods", namespace=namespace, context=context)
    if not result.success:
        return {"pods": [], "error": result.error}
    pods = sorted(
        (
            {
                "name": item.get("metadata", {}).get("name", ""),
                "status": item.get("status", {}).get("phase", "Unknown"),
            }
            for item in (result.parsed_json or {}).get("items", [])
            if item.get("metadata", {}).get("name")
        ),
        key=lambda item: item["name"],
    )
    return {"pods": pods, "error": None}
