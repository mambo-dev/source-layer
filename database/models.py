from sqlalchemy import Column, Integer, String,ForeignKey,DateTime,Text, UniqueConstraint
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime, timezone




class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    second_name = Column(String,  nullable=False)
    password_hash = Column(String,  nullable=False)


class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="pending")
    storage_path = Column(String, nullable=True)
    chunks = relationship(
        "DocumentChunks",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True
    )


class DocumentChunks(Base):
    __tablename__ = 'document_chunks'
    __table_args__ = (
            UniqueConstraint(
                "document_id",
                "page",
                "chunk_index",
                name="uq_document_page_chunk"
            ),
        )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey('documents.id', ondelete="CASCADE"), nullable=False)
    page = Column(Integer, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=True)
    document = relationship(
        "Document",
        back_populates="chunks"
    )