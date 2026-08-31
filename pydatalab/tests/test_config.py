from pathlib import Path

import pytest


def test_default_settings():
    from pydatalab.config import ServerConfig

    config = ServerConfig()
    assert config.MONGO_URI == "mongodb://localhost:27017/datalabvue"
    assert config.SECRET_KEY
    assert Path(config.FILE_DIRECTORY).name == "files"


def test_update_settings():
    from pydatalab.config import ServerConfig

    config = ServerConfig()
    new_settings = {
        "mongo_uri": "mongodb://test",
        "new_key": "some new data",
    }
    config.update(new_settings)

    assert new_settings["mongo_uri"] == config.MONGO_URI
    assert new_settings["new_key"] == config.NEW_KEY
    assert config.SECRET_KEY
    assert Path(config.FILE_DIRECTORY).name == "files"


def test_config_override():
    from pydatalab.main import create_app

    app = create_app(
        config_override={"REMOTE_FILESYSTEMS": [{"hostname": None, "path": "/", "name": "local"}]}
    )
    assert app.config["REMOTE_FILESYSTEMS"][0]["hostname"] is None
    assert app.config["REMOTE_FILESYSTEMS"][0]["path"] == Path("/")

    from pydatalab.config import CONFIG

    assert CONFIG.REMOTE_FILESYSTEMS[0].hostname is None
    assert CONFIG.REMOTE_FILESYSTEMS[0].path == Path("/")


def test_env_var_flask_config_override(secret_key):
    """Temporarily set an environment variable and check that it gets
    passed to the flask config correctly. Also make sure that the datalab
    secret key is preferred over the env var.
    """
    with pytest.MonkeyPatch.context() as m:
        from pydatalab.main import create_app

        m.setenv("FLASK_MAIL_PASSWORD_MOCK", "env_password")
        m.setenv("FLASK_SECRET_KEY", "too-short")
        app = create_app()
        assert app.config["MAIL_PASSWORD_MOCK"] == "env_password"  # noqa: S105
        assert app.config["SECRET_KEY"] == secret_key  # noqa: S105


def test_validators():
    from pydatalab.config import ServerConfig

    # check bad prefix
    with pytest.raises(
        RuntimeError, match="Identifier prefix must be less than 12 characters long,"
    ):
        _ = ServerConfig(IDENTIFIER_PREFIX="this prefix is way way too long", TESTING=False)


def test_label_printing_config():
    from pydatalab.config import LabelPrintingConfig, LabelPrintProfile

    profile = LabelPrintProfile(
        id="lab-label",
        name="Lab label",
        media_type="fixed",
        width_mm=40,
        height_mm=30,
        printable_width_mm=36,
        printable_height_mm=26,
        dpi=300,
        max_qr_size_mm=20,
    )
    config = LabelPrintingConfig(default_profile="lab-label", profiles=[profile])

    assert config.default_profile == "lab-label"
    assert config.profiles == [profile]


def test_info_serializes_label_printing_config():
    from pydatalab.routes.v0_1.info import Info, _get_deployment_metadata_once

    attributes = Info(**_get_deployment_metadata_once()).model_dump(mode="json")

    assert attributes["label_printing"] == {"default_profile": "a4-single", "profiles": []}


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"height_mm": None}, "require height_mm"),
        ({"printable_width_mm": 41}, "Printable width"),
        ({"printable_height_mm": 31}, "Printable height must fit"),
        ({"max_qr_size_mm": 37}, "Maximum QR size"),
        ({"max_qr_size_mm": 25}, "Printable height must fit the QR"),
        ({"media_type": "continuous"}, "must omit fixed height"),
    ],
)
def test_label_print_profile_dimension_validation(overrides, message):
    from pydatalab.config import LabelPrintProfile

    values = {
        "id": "lab-label",
        "name": "Lab label",
        "media_type": "fixed",
        "width_mm": 40,
        "height_mm": 30,
        "printable_width_mm": 36,
        "printable_height_mm": 26,
        "dpi": 300,
        "max_qr_size_mm": 20,
    }

    with pytest.raises(ValueError, match=message):
        LabelPrintProfile(**(values | overrides))


@pytest.mark.parametrize(
    "default_profile, profile_ids",
    [
        ("missing", []),
        ("a4-single", ["duplicate", "duplicate"]),
        ("a4-single", ["a4-single"]),
    ],
)
def test_label_printing_profile_id_validation(default_profile, profile_ids):
    from pydatalab.config import LabelPrintingConfig, LabelPrintProfile

    profiles = [
        LabelPrintProfile(
            id=profile_id,
            name=profile_id,
            media_type="continuous",
            width_mm=24,
            printable_width_mm=18,
            dpi=180,
            max_qr_size_mm=18,
        )
        for profile_id in profile_ids
    ]

    with pytest.raises(ValueError):
        LabelPrintingConfig(default_profile=default_profile, profiles=profiles)


def test_mail_settings_combinations(tmpdir):
    """Tests that the config file mail settings get passed
    correctly to the flask settings, and that additional
    overrides can be provided as environment variables.
    """

    from pydatalab.config import CONFIG, SMTPSettings
    from pydatalab.main import create_app

    CONFIG.update(
        {
            "EMAIL_AUTH_SMTP_SETTINGS": SMTPSettings(
                MAIL_SERVER="example.com",
                MAIL_DEFAULT_SENDER="test@example.com",
                MAIL_PORT=587,
                MAIL_USE_TLS=True,
                MAIL_USERNAME="user",
            )
        }
    )

    app = create_app()
    assert app.config["MAIL_SERVER"] == "example.com"
    assert app.config["MAIL_DEFAULT_SENDER"] == "test@example.com"
    assert app.config["MAIL_PORT"] == 587
    assert app.config["MAIL_USE_TLS"] is True
    assert app.config["MAIL_USERNAME"] == "user"

    # write temporary .env file and check that it overrides the config
    env_file = Path(tmpdir.join(".env"))
    env_file.write_text("MAIL_PASSWORD=password\nMAIL_DEFAULT_SENDER=test2@example.com")

    app = create_app(env_file=env_file)
    assert app.config["MAIL_PASSWORD"] == "password"  # noqa: S105
    assert app.config["MAIL_DEFAULT_SENDER"] == "test2@example.com"


def test_key_strength_checker():
    from pydatalab.feature_flags import _check_key_strength
    from pydatalab.main import create_app

    with pytest.raises(RuntimeError, match="Shannon entropy"):
        create_app({"SECRET_KEY": "short"})

    with pytest.raises(RuntimeError, match="Shannon entropy"):
        assert _check_key_strength("a" * 32)

    with pytest.raises(RuntimeError, match="Shannon entropy"):
        assert _check_key_strength("ab" * 16)

    assert _check_key_strength("abcdefghijklmnopqrstuvwxyz") is None
