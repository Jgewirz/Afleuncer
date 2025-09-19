#!/usr/bin/env python3
"""
Database migration runner for SkinStack
Applies any new *.sql files not recorded in schema_migrations table
"""
import asyncio
import asyncpg
import hashlib
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from lib.settings import settings

class MigrationRunner:
    def __init__(self, migrations_dir: Path = Path('sql/migrations')):
        self.migrations_dir = migrations_dir
        self.conn = None

    async def connect(self):
        """Establish database connection"""
        self.conn = await asyncpg.connect(str(settings.database_url))

    async def disconnect(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()

    async def ensure_migrations_table(self):
        """Create schema_migrations table if it doesn't exist"""
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ DEFAULT NOW(),
                execution_time_ms INTEGER
            )
        """)

        # Add new columns to existing table if needed
        await self.conn.execute("""
            ALTER TABLE schema_migrations
            ADD COLUMN IF NOT EXISTS checksum TEXT;
        """)

        await self.conn.execute("""
            ALTER TABLE schema_migrations
            ADD COLUMN IF NOT EXISTS execution_time_ms INTEGER;
        """)

    async def get_applied_migrations(self) -> Dict[int, str]:
        """Get list of already applied migrations"""
        rows = await self.conn.fetch("""
            SELECT version, COALESCE(checksum, '') as checksum
            FROM schema_migrations
            ORDER BY version
        """)
        return {row['version']: row['checksum'] for row in rows}

    def get_migration_files(self) -> List[Tuple[int, Path, str]]:
        """Get all migration files sorted by version"""
        migrations = []

        for file in self.migrations_dir.glob('*.sql'):
            # Extract version from filename (e.g., 001_clicks.sql -> 1)
            try:
                version = int(file.name.split('_')[0])
            except (ValueError, IndexError):
                print(f"[WARN] Skipping invalid migration filename: {file.name}")
                continue

            # Calculate checksum
            with open(file, 'rb') as f:
                content = f.read()
                checksum = hashlib.sha256(content).hexdigest()

            migrations.append((version, file, checksum))

        return sorted(migrations, key=lambda x: x[0])

    async def apply_migration(self, version: int, file: Path, checksum: str):
        """Apply a single migration"""
        name = file.stem
        start_time = asyncio.get_event_loop().time()

        print(f"[MIGRATE] Applying {name}...")

        try:
            # Read migration SQL
            with open(file, 'r', encoding='utf-8') as f:
                sql = f.read()

            # Execute in transaction
            async with self.conn.transaction():
                # Run the migration
                await self.conn.execute(sql)

                # Record in schema_migrations
                execution_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

                await self.conn.execute("""
                    INSERT INTO schema_migrations (version, name, checksum, execution_time_ms)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (version)
                    DO UPDATE SET
                        checksum = $3,
                        applied_at = NOW(),
                        execution_time_ms = $4
                """, version, name, checksum, execution_time_ms)

            print(f"[OK] {name} applied in {execution_time_ms}ms")

        except Exception as e:
            print(f"[ERROR] Failed to apply {name}: {e}")
            raise

    async def run(self, force: bool = False):
        """Run all pending migrations"""
        try:
            await self.connect()
            await self.ensure_migrations_table()

            # Get applied migrations
            applied = await self.get_applied_migrations()

            # Get all migration files
            migrations = self.get_migration_files()

            if not migrations:
                print("[INFO] No migration files found")
                return

            # Track stats
            pending = 0
            skipped = 0
            applied_count = 0

            for version, file, checksum in migrations:
                if version in applied:
                    if applied[version] == checksum:
                        print(f"[SKIP] {file.stem} already applied")
                        skipped += 1
                    elif force:
                        print(f"[FORCE] Re-applying {file.stem} (checksum changed)")
                        await self.apply_migration(version, file, checksum)
                        applied_count += 1
                    else:
                        print(f"[WARN] {file.stem} has changed but not re-applying (use --force)")
                        skipped += 1
                else:
                    pending += 1
                    await self.apply_migration(version, file, checksum)
                    applied_count += 1

            # Print summary
            print(f"\n[SUMMARY]")
            print(f"  Total migrations: {len(migrations)}")
            print(f"  Applied: {applied_count}")
            print(f"  Skipped: {skipped}")
            print(f"  Database: {settings.database_url.host}")

            # Verify final state
            await self.verify_schema()

        finally:
            await self.disconnect()

    async def verify_schema(self):
        """Verify the schema is in expected state"""
        # Get all tables
        tables = await self.conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)

        expected_tables = {
            'schema_migrations', 'tracking_links', 'clicks',
            'webhook_events', 'conversions', 'commissions',
            'payouts', 'programs', 'merchants', 'influencers',
            'attribution_windows'
        }

        actual_tables = {t['table_name'] for t in tables}
        missing_tables = expected_tables - actual_tables

        if missing_tables:
            print(f"[WARN] Missing expected tables: {', '.join(missing_tables)}")
        else:
            print(f"[OK] All {len(expected_tables)} expected tables present")

        # Check critical indexes
        indexes = await self.conn.fetch("""
            SELECT tablename, indexname
            FROM pg_indexes
            WHERE tablename IN ('clicks', 'tracking_links', 'conversions')
            AND schemaname = 'public'
        """)

        print(f"[OK] Found {len(indexes)} indexes on critical tables")

    async def rollback(self, target_version: int):
        """Rollback to a specific version (requires down migrations)"""
        print(f"[INFO] Rollback not implemented - would need down migrations")
        print(f"[INFO] To rollback, restore from backup and re-run migrations")

async def main():
    """CLI entry point"""
    force = '--force' in sys.argv
    rollback = '--rollback' in sys.argv

    if rollback and len(sys.argv) > 2:
        target = int(sys.argv[2])
        runner = MigrationRunner()
        await runner.rollback(target)
    else:
        runner = MigrationRunner()
        await runner.run(force=force)

if __name__ == "__main__":
    asyncio.run(main())