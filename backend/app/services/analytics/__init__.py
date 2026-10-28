"""Pure calculations for Cash & Credit Intelligence.

This package deliberately has no database, HTTP, or clock dependency.  The
future loader and router layers pass plain input rows and an explicit ``today``
to these calculations.
"""
