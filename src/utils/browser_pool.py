"""
Browser Pool for parallel Playwright automation.
Manages multiple browser sessions for concurrent processing.
"""

import logging
from queue import Queue
from playwright.sync_api import sync_playwright, Browser, Page


class BrowserPool:
    """
    Manages a pool of browser sessions for parallel processing.

    Example:
        pool = BrowserPool(pool_size=3)

        # Get a browser
        browser_session = pool.get_browser()

        # Use it
        browser_session['page'].goto('https://example.com')

        # Return it
        pool.return_browser(browser_session)

        # Cleanup
        pool.close_all()
    """

    def __init__(self, pool_size: int = 3):
        """
        Initialize browser pool.

        Args:
            pool_size: Number of parallel browsers to maintain
        """
        self.pool_size = pool_size
        self.browsers = Queue(maxsize=pool_size)
        self.playwright = None
        self.logger = logging.getLogger(__name__)

        self._initialize_pool()

    def _initialize_pool(self):
        """Create and login all browser instances."""
        self.logger.info(f"Initializing browser pool with {self.pool_size} browsers...")

        # Start playwright
        self.playwright = sync_playwright().start()

        # Create browser instances
        for i in range(self.pool_size):
            try:
                browser = self.playwright.chromium.launch(headless=True)
                page = browser.new_page()

                # Store browser session
                session = {
                    'id': i,
                    'browser': browser,
                    'page': page
                }

                self.browsers.put(session)
                self.logger.info(f"  Created browser {i+1}/{self.pool_size}")

            except Exception as e:
                self.logger.error(f"Failed to create browser {i}: {e}")
                raise

        self.logger.info(f"✓ Browser pool initialized with {self.pool_size} browsers")

    def get_browser(self) -> dict:
        """
        Get an available browser from the pool.
        Blocks if all browsers are busy.

        Returns:
            Browser session dict with 'id', 'browser', 'page'
        """
        session = self.browsers.get()  # Blocks until browser available
        self.logger.debug(f"Browser {session['id']} checked out from pool")
        return session

    def return_browser(self, session: dict):
        """
        Return a browser to the pool.

        Args:
            session: Browser session to return
        """
        self.browsers.put(session)
        self.logger.debug(f"Browser {session['id']} returned to pool")

    def close_all(self):
        """Close all browsers and cleanup."""
        self.logger.info("Closing all browsers in pool...")

        # Get all browsers from queue
        browsers_to_close = []
        while not self.browsers.empty():
            browsers_to_close.append(self.browsers.get())

        # Close each browser
        for session in browsers_to_close:
            try:
                session['page'].close()
                session['browser'].close()
                self.logger.debug(f"Closed browser {session['id']}")
            except Exception as e:
                self.logger.warning(f"Error closing browser {session['id']}: {e}")

        # Stop playwright
        if self.playwright:
            self.playwright.stop()

        self.logger.info("✓ All browsers closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup."""
        self.close_all()
        return False
