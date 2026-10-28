from app.llm.agent_api import embed_text
from app.database.models import  DocumentChunks 
from sqlalchemy import  select,func, cast, String
from itertools import islice
from sqlalchemy.dialects.postgresql import TSQUERY

def retrieve_top_embeddings(question, db, document_id, top_k =3):
    embedded_question = embed_text(question)[0]
    distance = DocumentChunks.embedding.cosine_distance(embedded_question)
    query = (select(DocumentChunks,(1 - distance).label("similarity")).
              where(DocumentChunks.embedding.is_not(None),DocumentChunks.document_id == document_id).
              order_by(distance).limit(top_k)
            )

    similarities = db.execute(query).all()

    return similarities



def retrieve_keyword_chunks(db, question,document_id, top_k=4):
    search_vector = func.to_tsvector(
        "english", DocumentChunks.text
    )


    search_query = func.plainto_tsquery(
        "english", 
        question
    )

    or_query = cast(func.replace(
        cast(search_query, String),
            " & ",
            " | "
    ),TSQUERY)

    rank = func.ts_rank(
        search_vector,
        or_query
    ) 

    stmnt = (
        select(DocumentChunks,rank.label("rank")).
        where(DocumentChunks.document_id == document_id, search_vector.op("@@")(or_query))
        .order_by(rank.desc(), DocumentChunks.id)
        .limit(top_k)
    )

    return db.execute(stmnt).all()


def reciprical_rank_fusion(
        vector_results,
        key_word_results,
        k=60,
        top_k = 4
):
    scores = {}
    chunks = {}
    for rank, (chunk, _) in enumerate(vector_results, start=1):
        if not chunk.id in scores:
            scores[chunk.id] = 0
        rank = 1 / (k + rank)
        scores[chunk.id] += rank
        chunks[chunk.id] = chunk
            
    for rank, (chunk, _) in enumerate(key_word_results, start=1):
        if not chunk.id in scores:
            scores[chunk.id] = 0
        rank = 1 / (k + rank)
        scores[chunk.id] += rank
        chunks[chunk.id] = chunk
  
    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    
    final_dict = {}
    
    for chunk_id, score in sorted_scores:
        final_dict[chunk_id] = {
            "chunk": chunks[chunk_id],
            "rrf_score": score
        }

    return dict(islice(final_dict.items(), top_k))



def retrieve_hybrid_chunks(question, document_id, db, top_k = 4):
    vector_results = retrieve_top_embeddings(question ,db, document_id, top_k=10)
    keyword_results = retrieve_keyword_chunks(db, question, document_id, top_k=10)
    
    return reciprical_rank_fusion(vector_results, keyword_results, top_k=top_k)
