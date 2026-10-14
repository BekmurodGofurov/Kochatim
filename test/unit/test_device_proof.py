"""
Unit tests — utils/device_proof.py

Pure cryptography, no Flask and no Redis: the key validation done at login and
the per-request signature check. The signer used here (conftest.sign_proof)
mirrors what the browser's WebCrypto produces; CrossLanguageVector pins a proof
made by the real JS code so the two sides cannot drift apart unnoticed.
"""
import base64
import json
import time

import pytest

from conftest import make_device_key, sign_proof
from utils.device_proof import (
    ProofError,
    jwk_thumbprint,
    normalize_public_jwk,
    proof_message,
    verify_proof,
)

PRIVATE, JWK = make_device_key()
OTHER_PRIVATE, OTHER_JWK = make_device_key()
CANON = normalize_public_jwk(JWK)
TOKEN = "session-token-abc"
TARGET = "/api/me/dashboard?x=1"
SKEW = 60


def _verify(header, *, method="GET", target=TARGET, token=TOKEN, jwk=CANON, now_ms=None):
    return verify_proof(header, method=method, target=target, token=token,
                        public_jwk=jwk, max_skew_seconds=SKEW, now_ms=now_ms)


def _b64u(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


# ─── normalize_public_jwk ─────────────────────────────────────────────────────

class TestNormalizePublicJwk:
    def test_accepts_a_real_key_and_returns_canonical_json(self):
        out = normalize_public_jwk(JWK)
        assert json.loads(out) == {"kty": "EC", "crv": "P-256", "x": JWK["x"], "y": JWK["y"]}
        assert out == json.dumps(json.loads(out), separators=(",", ":"), sort_keys=True)

    def test_extra_members_are_dropped(self):
        """WebCrypto adds ext / key_ops; none of it should be stored."""
        noisy = {**JWK, "ext": True, "key_ops": ["verify"], "alg": "ES256", "kid": "k1"}
        assert normalize_public_jwk(noisy) == CANON

    def test_member_order_does_not_matter(self):
        shuffled = {"y": JWK["y"], "x": JWK["x"], "crv": "P-256", "kty": "EC"}
        assert normalize_public_jwk(shuffled) == CANON

    @pytest.mark.parametrize("bad", [
        None, "", "x", 7, [], [JWK], {}, True,
    ])
    def test_non_objects_are_rejected(self, bad):
        with pytest.raises(ValueError):
            normalize_public_jwk(bad)

    def test_a_private_key_is_refused_outright(self):
        """If the browser ever sent 'd' we must not store it, or quietly accept it."""
        with pytest.raises(ValueError, match="public"):
            normalize_public_jwk({**JWK, "d": _b64u(b"\x01" * 32)})

    @pytest.mark.parametrize("override", [
        {"kty": "RSA"}, {"kty": "OKP"}, {"kty": None}, {"crv": "P-384"}, {"crv": "secp256k1"}, {"crv": None},
    ])
    def test_only_ec_p256_is_accepted(self, override):
        with pytest.raises(ValueError):
            normalize_public_jwk({**JWK, **override})

    @pytest.mark.parametrize("coord", [
        "", "AAAA", "!!!!", _b64u(b"\x01" * 31), _b64u(b"\x01" * 33), None, 5, [], "a b",
        "A" * 100,
    ])
    @pytest.mark.parametrize("which", ["x", "y"])
    def test_malformed_coordinates_are_rejected(self, which, coord):
        with pytest.raises(ValueError):
            normalize_public_jwk({**JWK, which: coord})

    def test_a_point_that_is_not_on_the_curve_is_rejected(self):
        with pytest.raises(ValueError):
            normalize_public_jwk({**JWK, "y": _b64u(b"\x07" * 32)})

    def test_missing_members_are_rejected(self):
        for drop in ("kty", "crv", "x", "y"):
            partial = {k: v for k, v in JWK.items() if k != drop}
            with pytest.raises(ValueError):
                normalize_public_jwk(partial)


# ─── jwk_thumbprint ───────────────────────────────────────────────────────────

class TestThumbprint:
    def test_is_deterministic(self):
        assert jwk_thumbprint(CANON) == jwk_thumbprint(CANON)

    def test_does_not_depend_on_extra_members(self):
        assert jwk_thumbprint(normalize_public_jwk({**JWK, "ext": True})) == jwk_thumbprint(CANON)

    def test_differs_between_keys(self):
        assert jwk_thumbprint(CANON) != jwk_thumbprint(normalize_public_jwk(OTHER_JWK))

    def test_is_43_char_base64url_sha256(self):
        tp = jwk_thumbprint(CANON)
        assert len(tp) == 43 and "=" not in tp and "+" not in tp and "/" not in tp


# ─── verify_proof ─────────────────────────────────────────────────────────────

class TestVerifyProof:
    def test_a_good_proof_returns_its_nonce(self):
        header = sign_proof(PRIVATE, TOKEN, "GET", TARGET, nonce="n" * 22)
        assert _verify(header) == "n" * 22

    def test_method_is_case_insensitive(self):
        header = sign_proof(PRIVATE, TOKEN, "get", TARGET)
        assert _verify(header, method="GET")

    def test_a_proof_for_one_method_does_not_cover_another(self):
        header = sign_proof(PRIVATE, TOKEN, "GET", TARGET)
        with pytest.raises(ProofError, match="bad_signature"):
            _verify(header, method="DELETE")

    @pytest.mark.parametrize("other", ["/api/me", "/api/me/dashboard", "/api/me/dashboard?x=2",
                                       "/api/me/dashboard?x=1&y=2", "/API/me/dashboard?x=1"])
    def test_a_proof_covers_exactly_one_path_and_query(self, other):
        header = sign_proof(PRIVATE, TOKEN, "GET", TARGET)
        with pytest.raises(ProofError, match="bad_signature"):
            _verify(header, target=other)

    def test_a_proof_is_bound_to_its_token(self):
        header = sign_proof(PRIVATE, TOKEN, "GET", TARGET)
        with pytest.raises(ProofError, match="bad_signature"):
            _verify(header, token=TOKEN + "x")

    def test_a_proof_from_another_key_is_rejected(self):
        header = sign_proof(OTHER_PRIVATE, TOKEN, "GET", TARGET)
        with pytest.raises(ProofError, match="bad_signature"):
            _verify(header)

    def test_a_tampered_signature_is_rejected(self):
        header = sign_proof(PRIVATE, TOKEN, "GET", TARGET)
        v, ts, nonce, sig = header.split(".")
        raw = bytearray(base64.urlsafe_b64decode(sig + "=="))
        raw[10] ^= 0x01
        with pytest.raises(ProofError, match="bad_signature"):
            _verify(".".join([v, ts, nonce, _b64u(bytes(raw))]))

    def test_changing_the_timestamp_or_nonce_breaks_the_signature(self):
        v, ts, nonce, sig = sign_proof(PRIVATE, TOKEN, "GET", TARGET).split(".")
        now = int(ts)
        with pytest.raises(ProofError, match="bad_signature"):
            _verify(".".join([v, str(now + 1), nonce, sig]), now_ms=now)
        with pytest.raises(ProofError, match="bad_signature"):
            _verify(".".join([v, ts, "z" * 22, sig]), now_ms=now)

    def test_a_der_encoded_signature_is_not_accepted_as_raw(self):
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        ts, nonce = str(int(time.time() * 1000)), "n" * 22
        der = PRIVATE.sign(proof_message(ts, nonce, "GET", TARGET, TOKEN), ec.ECDSA(hashes.SHA256()))
        with pytest.raises(ProofError):
            _verify(f"v1.{ts}.{nonce}.{_b64u(der)}")

    # --- freshness ------------------------------------------------------------

    def test_exactly_at_the_skew_limit_is_still_valid(self):
        now = 1_800_000_000_000
        header = sign_proof(PRIVATE, TOKEN, "GET", TARGET, ts_ms=now - SKEW * 1000)
        assert _verify(header, now_ms=now)

    def test_one_millisecond_past_the_limit_is_stale(self):
        now = 1_800_000_000_000
        header = sign_proof(PRIVATE, TOKEN, "GET", TARGET, ts_ms=now - SKEW * 1000 - 1)
        with pytest.raises(ProofError, match="stale"):
            _verify(header, now_ms=now)

    def test_a_clock_running_ahead_is_tolerated_up_to_the_limit_then_refused(self):
        now = 1_800_000_000_000
        assert _verify(sign_proof(PRIVATE, TOKEN, "GET", TARGET, ts_ms=now + SKEW * 1000), now_ms=now)
        with pytest.raises(ProofError, match="stale"):
            _verify(sign_proof(PRIVATE, TOKEN, "GET", TARGET, ts_ms=now + SKEW * 1000 + 1), now_ms=now)

    def test_uses_the_real_clock_by_default(self):
        assert _verify(sign_proof(PRIVATE, TOKEN, "GET", TARGET))
        with pytest.raises(ProofError, match="stale"):
            _verify(sign_proof(PRIVATE, TOKEN, "GET", TARGET, ts_ms=(time.time() - 600) * 1000))

    # --- malformed input never raises anything but ProofError ----------------

    @pytest.mark.parametrize("header,reason", [
        (None, "missing"), ("", "missing"),
        ("garbage", "malformed"), ("v1", "malformed"), ("v1.1.2", "malformed"),
        ("v1.1.2.3.4", "malformed"), ("v2.1.abcdefghijklmnop.AAAA", "malformed"),
        ("v1.abc.abcdefghijklmnop.AAAA", "malformed"),
        ("v1.-5.abcdefghijklmnop.AAAA", "malformed"),
        ("v1." + "9" * 16 + ".abcdefghijklmnop.AAAA", "malformed"),
        ("v1.1700000000000.short.AAAA", "malformed"),
        ("v1.1700000000000." + "a" * 65 + ".AAAA", "malformed"),
        ("v1.1700000000000.abc!efghijklmnopq.AAAA", "malformed"),
    ])
    def test_structurally_invalid_headers(self, header, reason):
        with pytest.raises(ProofError, match=reason):
            _verify(header, now_ms=1_700_000_000_000)

    @pytest.mark.parametrize("sig", ["", "AAAA", "!!!", "A" * 85, "A" * 87, _b64u(b"\x00" * 64)])
    def test_bad_signature_encodings(self, sig):
        now = 1_700_000_000_000
        with pytest.raises(ProofError):
            _verify(f"v1.{now}.abcdefghijklmnop.{sig}", now_ms=now)

    def test_a_corrupt_stored_key_fails_closed(self):
        header = sign_proof(PRIVATE, TOKEN, "GET", TARGET)
        for bad in ("not json", "{}", '{"x":"a","y":"b","kty":"EC","crv":"P-256"}'):
            with pytest.raises(ProofError):
                _verify(header, jwk=bad)


# ─── Pinned vector from the browser's own signer ────────────────────────────────

class TestCrossLanguageVector:
    """
    A proof produced by client/src/api/deviceKey.js running on real WebCrypto
    (see test/fixtures/device_proof_vector.json). If either side changes the
    message layout or the signature encoding, this fails.
    """
    def test_proof_made_by_the_javascript_client_verifies(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "device_proof_vector.json")
        with open(path) as f:
            v = json.load(f)
        ts = int(v["proof"].split(".")[1])
        jwk = normalize_public_jwk(v["publicJwk"])
        nonce = verify_proof(
            v["proof"], method=v["method"], target=v["target"], token=v["token"],
            public_jwk=jwk, max_skew_seconds=60, now_ms=ts,
        )
        assert nonce == v["proof"].split(".")[2]

    def test_the_vector_does_not_verify_against_a_different_path(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "device_proof_vector.json")
        with open(path) as f:
            v = json.load(f)
        with pytest.raises(ProofError):
            verify_proof(v["proof"], method=v["method"], target=v["target"] + "x", token=v["token"],
                         public_jwk=normalize_public_jwk(v["publicJwk"]), max_skew_seconds=60,
                         now_ms=int(v["proof"].split(".")[1]))
