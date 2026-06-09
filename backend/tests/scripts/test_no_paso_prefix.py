import subprocess
import sys


def test_legacy_file_allowed():
    """paso6_aws_connector.py existente no falla."""
    result = subprocess.run(
        [sys.executable, "backend/scripts/ruff_rules/no_paso_prefix.py",
         "backend/app/motors/m22_discovery/paso6_aws_connector.py"],
        capture_output=True
    )
    assert result.returncode == 0


def test_new_paso_prefix_fails():
    """Nuevo paso10_*.py falla."""
    import tempfile
    # NOTA: usamos prefix= en vez de suffix= porque NamedTemporaryFile genera
    # ${dir}/${prefix}${random}${suffix}; con suffix="paso10_test.py" el nombre
    # final no empieza por "paso\d+_" y el regex no matchea (bug en plan v4.2).
    with tempfile.NamedTemporaryFile(prefix="paso10_", suffix=".py", delete=False) as f:
        result = subprocess.run(
            [sys.executable, "backend/scripts/ruff_rules/no_paso_prefix.py", f.name],
            capture_output=True
        )
        assert result.returncode == 1
        assert b"PASO_PREFIX_FORBIDDEN" in result.stderr


def test_normal_file_allowed():
    """fichero normal sin prefijo paso pasa."""
    result = subprocess.run(
        [sys.executable, "backend/scripts/ruff_rules/no_paso_prefix.py",
         "backend/app/motors/m29_client_messaging/service.py"],
        capture_output=True
    )
    assert result.returncode == 0
