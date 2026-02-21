"""
DEPRECATED: This file is kept for backward compatibility only.

All functionality has been moved to:
- lib/etf/functions/core/ - Core operations (NAV, accounting, workflows)
- lib/etf/functions/operations/ - Operational functions (TA, OM, distributions)
- lib/etf/functions/compliance/ - Compliance and audit
- lib/etf/functions/tax/ - Tax functions

Please update your imports to use the new structure:
    from lib.etf.functions.core import FundAdministration, Accounting
    from lib.etf.functions.operations import TransferAgent, OrderManagement, Distributor

This file will be removed in a future version.
"""

import warnings

warnings.warn(
    "lib.self_service_functions is deprecated. "
    "Please use lib.etf.functions.core and lib.etf.functions.operations instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for backward compatibility
from lib.etf.functions.core import FundAdministration, Accounting
from lib.etf.functions.operations import TransferAgent, OrderManagement, Distributor

# Keep old class names for compatibility
SelfServiceFunctionsManager = None  # Deprecated - use DailyOrchestrator instead

__all__ = [
    'FundAdministration',
    'Accounting',
    'TransferAgent',
    'OrderManagement',
    'Distributor',
]
