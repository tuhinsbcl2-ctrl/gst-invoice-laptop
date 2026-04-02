"""
Smoke tests for the GST Billing Application.
Tests that all critical pages load without errors.
"""
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client


SMOKE_URLS = [
    '/',
    '/invoice/',
    '/invoice/create',
    '/customer/',
    '/customer/create',
    '/supplier/',
    '/supplier/create',
    '/product/',
    '/expense/',
    '/expense/create',
    '/purchase/',
    '/purchase/create',
    '/accounts/',
    '/returns/purchase/',
    '/returns/sales/',
    '/returns/purchase/create',
    '/returns/sales/create',
    '/reports/',
    '/reports/profit-loss',
    '/reports/balance-sheet',
    '/reports/gstr1',
    '/reports/gstr2b',
    '/reports/gstr3b',
    '/bank/',
    '/settings/',
]


@pytest.mark.parametrize('url', SMOKE_URLS)
def test_page_loads(client, url):
    """Each URL should return 200 OK."""
    response = client.get(url)
    assert response.status_code == 200, (
        f'{url} returned {response.status_code}'
    )
