"""Background task scheduler for data refresh and spinoff monitoring."""

import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def refresh_watchlist_data():
    """Refresh stock data for all watchlist items."""
    logger.info("Starting watchlist data refresh...")
    
    try:
        from app.db.database import async_session
        from app.db.repositories import WatchlistRepository
        from app.services.data_fetcher import DataFetcherService
        
        async with async_session() as session:
            repo = WatchlistRepository(session)
            items = await repo.get_all()
            
            if not items:
                logger.info("No watchlist items to refresh")
                return
            
            symbols = [item.symbol for item in items]
            logger.info(f"Refreshing data for {len(symbols)} stocks")
            
            fetcher = DataFetcherService()
            stocks = await fetcher.fetch_stocks(symbols)
            
            logger.info(f"Successfully refreshed {len(stocks)} stocks")
            
    except Exception as e:
        logger.error(f"Error refreshing watchlist data: {e}")


async def check_new_spinoffs():
    """Check SEC EDGAR for new spinoff filings."""
    logger.info("Checking for new spinoffs...")
    
    try:
        from app.db.database import async_session
        from app.db.repositories import SpinoffRepository
        from app.services.sec_monitor import SECMonitorService
        
        sec_service = SECMonitorService()
        filings = await sec_service.get_recent_spinoff_filings(days=7)
        
        if not filings:
            logger.info("No new spinoff filings found")
            return
        
        async with async_session() as session:
            repo = SpinoffRepository(session)
            existing = await repo.get_all()
            existing_names = {s.spinoff_name for s in existing}
            
            new_count = 0
            for filing in filings:
                spinoff = await sec_service.parse_spinoff_filing(filing)
                if spinoff and spinoff.spinoff_name not in existing_names:
                    saved = await repo.add(spinoff)
                    
                    # Create alert
                    await repo.create_alert(
                        spinoff_id=saved.id,
                        title=f"New Spinoff: {spinoff.spinoff_name}",
                        message=f"New spinoff detected: {spinoff.spinoff_name} (Form {spinoff.sec_filing_type})",
                    )
                    new_count += 1
                    logger.info(f"New spinoff detected: {spinoff.spinoff_name}")
            
            if new_count:
                logger.info(f"Added {new_count} new spinoffs")
            else:
                logger.info("No new spinoffs to add")
                
    except Exception as e:
        logger.error(f"Error checking spinoffs: {e}")


def start_scheduler():
    """Start the background scheduler."""
    if scheduler.running:
        logger.warning("Scheduler already running")
        return
    
    # Add jobs
    scheduler.add_job(
        refresh_watchlist_data,
        trigger=IntervalTrigger(hours=settings.refresh_interval_hours),
        id="refresh_watchlist",
        name="Refresh watchlist stock data",
        replace_existing=True,
    )
    
    scheduler.add_job(
        check_new_spinoffs,
        trigger=IntervalTrigger(hours=6),  # Check 4x daily
        id="check_spinoffs",
        name="Check for new spinoffs",
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


async def trigger_manual_refresh():
    """Manually trigger a data refresh (for API endpoint)."""
    await refresh_watchlist_data()


async def trigger_spinoff_check():
    """Manually trigger spinoff check (for API endpoint)."""
    await check_new_spinoffs()

