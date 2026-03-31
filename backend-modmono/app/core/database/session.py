"""
FastAPI dependency injection for SQLAlchemy sessions.

Provides request-scoped database session handling and
dependency injection for route handlers.
"""
from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database.connection import get_database, DatabaseConnection
from app.core.utils.logging import get_logger

logger = get_logger(__name__)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database session.
    
    Provides a database session for the duration of a request.
    Automatically handles session lifecycle, commits, and rollbacks.
    
    Usage:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload, joinedload
        
        # 1. Simple single-table query
        @router.get("/users")
        async def get_users(session: AsyncSession = Depends(get_db_session)):
            result = await session.execute(select(User))
            users = result.scalars().all()
            return users
        
        # 2. Join with WHERE clause (INNER JOIN)
        @router.get("/user-agents")
        async def get_user_agents(session: AsyncSession = Depends(get_db_session)):
            stmt = (
                select(User, Agent)
                .join(UserAgent, User.id == UserAgent.user_id)
                .join(Agent, Agent.id == UserAgent.agent_id)
                .where(User.is_active == True)
            )
            result = await session.execute(stmt)
            # Returns tuples of (User, Agent)
            user_agents = result.all()
            return user_agents
        
        # 3. LEFT JOIN with outerjoin()
        @router.get("/users-with-agents")
        async def get_users_with_agents(session: AsyncSession = Depends(get_db_session)):
            stmt = (
                select(User, Agent)
                .outerjoin(UserAgent, User.id == UserAgent.user_id)
                .outerjoin(Agent, Agent.id == UserAgent.agent_id)
            )
            result = await session.execute(stmt)
            return result.all()
        
        # 4. Eager loading relationships (most efficient for nested data)
        @router.get("/agents-with-users")
        async def get_agents_with_users(session: AsyncSession = Depends(get_db_session)):
            # selectinload: separate query for relationships
            stmt = select(Agent).options(selectinload(Agent.users))
            result = await session.execute(stmt)
            agents = result.scalars().all()
            # agents[0].users is now loaded without extra queries
            return agents
        
        # 5. Complex multi-table join
        @router.get("/audit-logs-enriched")
        async def get_enriched_audit_logs(session: AsyncSession = Depends(get_db_session)):
            stmt = (
                select(AuditLog, User, Agent)
                .join(User, AuditLog.actor_id == User.id)
                .outerjoin(Agent, AuditLog.resource_id == Agent.id)
                .where(AuditLog.action.in_(['CREATE', 'UPDATE']))
                .order_by(AuditLog.timestamp.desc())
                .limit(100)
            )
            result = await session.execute(stmt)
            return result.all()
        
        # 6. Aggregation with joins
        @router.get("/user-stats")
        async def get_user_stats(session: AsyncSession = Depends(get_db_session)):
            from sqlalchemy import func
            
            stmt = (
                select(
                    User.id,
                    User.username,
                    func.count(UserAgent.agent_id).label('agent_count')
                )
                .outerjoin(UserAgent, User.id == UserAgent.user_id)
                .group_by(User.id, User.username)
            )
            result = await session.execute(stmt)
            return result.all()
        
        # 7. Create with transaction
        @router.post("/users")
        async def create_user(
            data: UserCreate,
            session: AsyncSession = Depends(get_db_session)
        ):
            user = User(**data.dict())
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
    
    Yields:
        AsyncSession instance
    """
    db: DatabaseConnection = get_database()
    
    if db is None or not db.is_connected:
        logger.error("Database not initialized or not connected")
        raise RuntimeError("Database connection not initialized. Call init_database() first.")
    
    async with db.session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            raise


async def get_db() -> DatabaseConnection:
    """
    FastAPI dependency for DatabaseConnection instance.
    
    Use this when you need direct access to the database connection
    for raw queries or connection management.
    
    Usage:
        @router.get("/health")
        async def health_check(db: DatabaseConnection = Depends(get_db)):
            is_healthy = await db.health_check()
            return {"status": "healthy" if is_healthy else "unhealthy"}
    
    Returns:
        DatabaseConnection instance
    """
    db = get_database()
    
    if db is None or not db.is_connected:
        logger.error("Database not initialized or not connected")
        raise RuntimeError("Database connection not initialized. Call init_database() first.")
    
    return db
