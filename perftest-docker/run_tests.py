import sys
import os

# Act as if we're in the project's root directory.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

FORCE=True

import impl_cad_basic
import impl_column_based
import impl_column_intermediate

impl_cad_basic.perftest_until_n(3, force=FORCE)
impl_column_based.perftest_until_n(3, force=FORCE)
impl_column_intermediate.perftest_until_n(3, force=FORCE)
