##############################################################################
#
# Copyright (c) 2009 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

from relstorage.adapters.interfaces import IConnectionManager
from zope.interface import implements
from ZODB.POSException import StorageError

class AbstractConnectionManager(object):
    """Abstract base class for connection management.

    Responsible for opening and closing database connections.
    """
    implements(IConnectionManager)

    # disconnected_exceptions contains the exception types that might be
    # raised when the connection to the database has been broken.
    disconnected_exceptions = ()

    # close_exceptions contains the exception types to ignore
    # when the adapter attempts to close a database connection.
    close_exceptions = ()

    # on_store_opened is either None or a callable that
    # will be called whenever a store cursor is opened or rolled back.
    on_store_opened = None

    def set_on_store_opened(self, f):
        """Set the on_store_opened hook"""
        self.on_store_opened = f

    def open(self):
        """Open a database connection and return (conn, cursor)."""
        raise NotImplementedError()

    def close(self, conn, cursor):
        """Close a connection and cursor, ignoring certain errors.
        """
        for obj in (cursor, conn):
            if obj is not None:
                try:
                    obj.close()
                except self.close_exceptions:
                    pass

    def open_and_call(self, callback):
        """Call a function with an open connection and cursor.

        If the function returns, commits the transaction and returns the
        result returned by the function.
        If the function raises an exception, aborts the transaction
        then propagates the exception.
        """
        conn, cursor = self.open()
        try:
            try:
                res = callback(conn, cursor)
            except:
                conn.rollback()
                raise
            else:
                conn.commit()
                return res
        finally:
            self.close(conn, cursor)

    def open_for_load(self):
        raise NotImplementedError()

    def restart_load(self, conn, cursor):
        """Reinitialize a connection for loading objects."""
        try:
            conn.rollback()
        except self.disconnected_exceptions, e:
            raise StorageError(e)

    def open_for_store(self):
        """Open and initialize a connection for storing objects.

        Returns (conn, cursor).
        """
        conn, cursor = self.open()
        try:
            if self.on_store_opened is not None:
                self.on_store_opened(cursor, restart=False)
            return conn, cursor
        except:
            self.close(conn, cursor)
            raise

    def restart_store(self, conn, cursor):
        """Reuse a store connection."""
        try:
            conn.rollback()
            if self.on_store_opened is not None:
                self.on_store_opened(cursor, restart=True)
        except self.disconnected_exceptions, e:
            raise StorageError(e)

    def open_for_pre_pack(self):
        """Open a connection to be used for the pre-pack phase.
        Returns (conn, cursor).
        """
        return self.open()
