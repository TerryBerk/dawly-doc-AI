"""
Query API endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from app.services.query_processor import QueryProcessor
from app.services.search_service import get_search_service
from app.services.reranker import Reranker
from app.services.context_builder import ContextBuilder
from app.services.confidence_scorer import ConfidenceScorer

logger = logging.getLogger(__name__)
router = APIRouter()


class QuerySource(BaseModel):
    """Source reference from documentation"""
    page: int
    section: Optional[str] = None
    confidence: float
    excerpt: str
    device_name: Optional[str] = None
    manufacturer: Optional[str] = None


class QueryRequest(BaseModel):
    """Query request model"""
    device_id: Optional[str] = Field(None, description="Device ID to query about")
    question: str = Field(..., description="User question")
    max_results: int = Field(5, ge=1, le=20, description="Maximum number of results")
    use_hybrid_search: bool = Field(True, description="Use hybrid search (semantic + keyword)")


class QueryResponse(BaseModel):
    """Query response model"""
    answer: str
    sources: List[QuerySource]
    confidence: float
    confidence_level: str
    device_id: Optional[str] = None
    query_metadata: dict = {}


@router.post("/query", response_model=QueryResponse)
async def query_documentation(request: QueryRequest):
    """
    Query device documentation using RAG
    
    Pipeline:
    1. Process and embed query
    2. Search Elasticsearch (k-NN + keyword)
    3. Re-rank results
    4. Build context
    5. Calculate confidence
    6. Extract sources
    7. Return formatted response
    
    Note: Returns context for frontend to use with LLM (OpenRouter)
    """
    try:
        logger.info(f"Query: {request.question[:100]}")
        
        # Step 1: Process query
        query_processor = QueryProcessor()
        processed_query = query_processor.process_query(
            request.question,
            device_id=request.device_id,
            expand=True
        )
        
        logger.debug(f"Query language: {processed_query.language}")
        
        # Step 2: Search Elasticsearch
        search_service = get_search_service()
        search_results = await search_service.search(
            query_embedding=processed_query.embedding,
            query_text=processed_query.cleaned_query,
            device_id=request.device_id,
            k=request.max_results * 2,  # Get more for re-ranking
            use_hybrid=request.use_hybrid_search
        )
        
        if not search_results:
            logger.warning("No search results found")
            return QueryResponse(
                answer="No relevant documentation found for your question. Please try rephrasing or check if the device documentation has been indexed.",
                sources=[],
                confidence=0.0,
                confidence_level="low",
                device_id=request.device_id,
                query_metadata={
                    "language": processed_query.language,
                    "results_found": 0
                }
            )
        
        logger.debug(f"Found {len(search_results)} search results")
        
        # Step 3: Re-rank results
        reranker = Reranker(relevance_threshold=0.1)
        reranked_results = reranker.rerank(
            processed_query.cleaned_query,
            search_results,
            top_k=request.max_results
        )
        
        logger.debug(f"Re-ranked to {len(reranked_results)} results")
        
        # Step 4: Build context
        context_builder = ContextBuilder(max_tokens=3000)
        context = context_builder.build_context(
            reranked_results,
            device_id=request.device_id
        )
        
        # Step 5: Calculate confidence
        confidence_scorer = ConfidenceScorer()
        confidence = confidence_scorer.calculate_confidence(
            search_results,
            reranked_results,
            context,
            processed_query.cleaned_query
        )
        
        confidence_level = confidence_scorer.get_confidence_level(confidence)
        
        logger.debug(f"Confidence: {confidence:.3f} ({confidence_level})")
        
        # Step 6: Extract sources
        sources_data = context_builder.build_sources(reranked_results)
        sources = [QuerySource(**source) for source in sources_data]
        
        # Step 7: Format response
        # Return context for frontend to use with LLM
        answer = context
        
        # Add confidence message
        confidence_msg = confidence_scorer.get_confidence_message(confidence)
        if confidence_msg:
            answer = f"{answer}\n\n---\nNote: {confidence_msg}"
        
        # Query metadata
        metadata = {
            "language": processed_query.language,
            "results_found": len(search_results),
            "reranked_results": len(reranked_results),
            "intent": query_processor.extract_intent(request.question),
            "is_connection_query": query_processor.is_connection_query(request.question),
            "search_type": "hybrid" if request.use_hybrid_search else "semantic"
        }
        
        logger.info(f"Query completed: {len(sources)} sources, confidence: {confidence:.3f}")
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            confidence=confidence,
            confidence_level=confidence_level,
            device_id=request.device_id,
            query_metadata=metadata
        )
    
    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query/history")
async def get_query_history(
    device_id: Optional[str] = None,
    limit: int = 10
):
    """
    Get query history
    
    TODO: Implement query history storage in database
    """
    # For now, return empty
    return {
        "queries": [],
        "total": 0,
        "message": "Query history not yet implemented"
    }


@router.get("/query/devices")
async def list_indexed_devices():
    """
    List devices with indexed documentation
    
    Returns devices available for querying
    """
    try:
        from app.services.elasticsearch_service import get_elasticsearch_service
        
        es_service = get_elasticsearch_service()
        
        # Get unique devices from index
        try:
            response = es_service.client.search(
                index=es_service.index_name,
                body={
                    "size": 0,
                    "aggs": {
                        "devices": {
                            "terms": {
                                "field": "device_id",
                                "size": 100
                            },
                            "aggs": {
                                "device_info": {
                                    "top_hits": {
                                        "size": 1,
                                        "_source": [
                                            "device_name",
                                            "manufacturer",
                                            "filename"
                                        ]
                                    }
                                }
                            }
                        }
                    }
                }
            )
            
            devices = []
            for bucket in response['aggregations']['devices']['buckets']:
                device_id = bucket['key']
                doc_count = bucket['doc_count']
                
                # Get device info from top hit
                top_hit = bucket['device_info']['hits']['hits'][0]['_source']
                
                devices.append({
                    "device_id": device_id,
                    "device_name": top_hit.get('device_name', ''),
                    "manufacturer": top_hit.get('manufacturer', ''),
                    "chunk_count": doc_count,
                    "filename": top_hit.get('filename', '')
                })
            
            return {
                "devices": devices,
                "count": len(devices)
            }
        
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return {
                "devices": [],
                "count": 0,
                "error": str(e)
            }
    
    except Exception as e:
        logger.error(f"List devices error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
