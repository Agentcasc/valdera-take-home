"""Relevance reranking using BGE or Cohere models."""
import os
import math

# Global model cache for BGE
_model = None
_tokenizer = None


def load_local_bge():
    """Load BGE reranker model locally (cached)."""
    global _model, _tokenizer
    
    if _model is None:
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            
            model_name = "BAAI/bge-reranker-v2-m3"
            _tokenizer = AutoTokenizer.from_pretrained(model_name)
            _model = AutoModelForSequenceClassification.from_pretrained(
                model_name, 
                trust_remote_code=True
            )
            print(f"Loaded BGE reranker: {model_name}")
        except ImportError as e:
            raise ImportError(
                "BGE reranker requires transformers and torch. "
                f"Install with: pip install transformers torch. Error: {e}"
            )
    
    return _model, _tokenizer


def rerank_score_bge(query: str, text: str) -> float:
    """
    Score relevance using local BGE reranker model.
    
    Args:
        query: Search query (e.g., "N-Methyl-2-pyrrolidone 872-50-4")
        text: Text to score against query
        
    Returns:
        Relevance score between 0 and 1
    """
    try:
        import torch
        
        model, tokenizer = load_local_bge()
        
        # Prepare inputs
        inputs = tokenizer(
            [[query, text]], 
            padding=True, 
            truncation=True, 
            return_tensors="pt",
            max_length=512
        )
        
        # Get relevance score
        with torch.no_grad():
            logits = model(**inputs).logits
        
        # Convert logits to probability using sigmoid
        score = 1 / (1 + math.exp(-float(logits[0][0])))
        return score
        
    except Exception as e:
        print(f"BGE scoring error: {e}")
        return 0.0


def rerank_score_cohere(query: str, text: str) -> float:
    """
    Score relevance using Cohere Rerank API.
    
    Args:
        query: Search query
        text: Text to score against query
        
    Returns:
        Relevance score between 0 and 1
    """
    try:
        import cohere
        
        api_key = os.environ.get("COHERE_API_KEY")
        if not api_key:
            raise ValueError("COHERE_API_KEY environment variable required")
        
        co = cohere.Client(api_key)
        
        response = co.rerank(
            model="rerank-v3.5",
            query=query,
            documents=[{"text": text}],
            top_n=1
        )
        
        if response.results:
            return float(response.results[0].relevance_score)
        return 0.0
        
    except Exception as e:
        print(f"Cohere scoring error: {e}")
        return 0.0


def rerank_score(query: str, text: str, method: str = "auto") -> float:
    """
    Score text relevance to query using the best available method.
    
    Args:
        query: Search query
        text: Text to score
        method: "bge", "cohere", or "auto" (tries Cohere first, falls back to BGE)
        
    Returns:
        Relevance score between 0 and 1
    """
    if method == "bge":
        return rerank_score_bge(query, text)
    elif method == "cohere":
        return rerank_score_cohere(query, text)
    elif method == "auto":
        # Try Cohere first (faster), fall back to BGE
        if os.environ.get("COHERE_API_KEY"):
            score = rerank_score_cohere(query, text)
            if score > 0:  # If Cohere worked
                return score
        
        # Fall back to local BGE
        return rerank_score_bge(query, text)
    else:
        raise ValueError(f"Unknown rerank method: {method}")


def batch_rerank(query: str, texts: list[str], method: str = "auto") -> list[float]:
    """
    Score multiple texts against a query.
    
    Args:
        query: Search query
        texts: List of texts to score
        method: Reranking method to use
        
    Returns:
        List of relevance scores
    """
    return [rerank_score(query, text, method) for text in texts]
