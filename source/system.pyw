import os
import json
import subprocess
import shutil
import argparse

import minecraft_launcher_lib


# ==============================
# GLOBALS
# ==============================

MINECRAFT_DIR = ""
CONFIG_FILE = ""


# ==============================
# ARGUMENTS FROM BAT
# ==============================

def get_arguments():

    parser = argparse.ArgumentParser()


    parser.add_argument(
        "--name",
        required=True
    )


    parser.add_argument(
        "--version",
        required=True
    )


    return parser.parse_args()



# ==============================
# CONFIGURATION
# ==============================

def load_configuration():

    global MINECRAFT_DIR
    global CONFIG_FILE


    launcher_folder = os.path.join(
        os.path.expanduser("~"),
        ".mcf"
    )


    if not os.path.exists(launcher_folder):

        os.makedirs(
            launcher_folder
        )


    CONFIG_FILE = os.path.join(
        launcher_folder,
        "settings.json"
    )


    default = {
    "minecraft_dir": launcher_folder,
    "last_username": "Player",
    "last_version": ""
}


    if os.path.exists(CONFIG_FILE):

        try:

            with open(
                CONFIG_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                saved = json.load(file)

                default.update(saved)


        except:

            pass



    MINECRAFT_DIR = os.path.normpath(
        default["minecraft_dir"]
    )


    return default



def save_configuration(data):

    try:

        with open(
            CONFIG_FILE,
            "w",
            encoding="utf-8"
        ) as file:


            json.dump(
                data,
                file,
                indent=4
            )


    except:

        pass
# ==============================
# JAVA
# ==============================


def get_java(version):


    try:

        runtime = (
            minecraft_launcher_lib.runtime
            .get_version_runtime_information(
                version,
                MINECRAFT_DIR
            )
        )


        if runtime:


            java = (
                minecraft_launcher_lib.runtime
                .get_executable_path(
                    runtime["name"],
                    MINECRAFT_DIR
                )
            )


            if java and os.path.exists(java):

                return java



    except:

        pass



    system_java = shutil.which(
        "java"
    )


    if system_java:

        return system_java



    return "java"





# ==============================
# JAVA INSTALL
# ==============================


def install_java(version):


    try:


        runtime_info = (
            minecraft_launcher_lib.runtime
            .get_version_runtime_information(
                version,
                MINECRAFT_DIR
            )
        )


        if runtime_info:


            java_name = runtime_info["name"]


            java_path = (
                minecraft_launcher_lib.runtime
                .get_executable_path(
                    java_name,
                    MINECRAFT_DIR
                )
            )


            if not java_path:


                print(
                    "Installing Java..."
                )


                minecraft_launcher_lib.runtime.install_jvm_runtime(

                    jvm_version=java_name,

                    minecraft_directory=MINECRAFT_DIR

                )



    except Exception as error:


        print(
            "Java error:",
            error
        )





# ==============================
# CHECK MINECRAFT VERSION
# ==============================


def version_exists(version):

    version_folder = os.path.join(
        MINECRAFT_DIR,
        "versions",
        version
    )

    json_file = os.path.join(
        version_folder,
        version + ".json"
    )

    jar_file = os.path.join(
        version_folder,
        version + ".jar"
    )

    return (
        os.path.exists(json_file)
        and
        os.path.exists(jar_file)
    )





# ==============================
# INSTALL MINECRAFT
# ==============================


def install_minecraft(version):


    if version_exists(version):


        print(
            "Version already installed."
        )


        return



    print(
        "Downloading Minecraft",
        version
    )



    minecraft_launcher_lib.install.install_minecraft_version(


        version=version,


        minecraft_directory=MINECRAFT_DIR,


        callback={


            "setStatus":

                lambda text:

                print(text),



            "setMax":

                lambda value:

                None,



            "setProgress":

                lambda progress:

                print(
                    "Progress:",
                    progress
                )


        }


    )
# ==============================
# LAUNCH MINECRAFT
# ==============================


def launch_minecraft(name, version):


    print(
        "Preparing Minecraft..."
    )


    print(
        "Player:",
        name
    )


    print(
        "Version:",
        version
    )



    # JAVA

    install_java(
        version
    )



    # MINECRAFT

    install_minecraft(
        version
    )


    if not version_exists(version):

        print(
            "Minecraft installation failed."
        )

        return



    print(
        "Creating command..."
    )



    options = {


        "username":

            name,



        "uuid":

            "00000000-0000-0000-0000-000000000000",



        "token":

            "0",



        "launcherName":

            "Simple Launcher",



        "launcherVersion":

            "1.0",



        "gameDirectory":

            MINECRAFT_DIR


    }





    command = (

        minecraft_launcher_lib.command
        .get_minecraft_command(

            version=version,

            minecraft_directory=MINECRAFT_DIR,

            options=options

        )

    )



    java = get_java(
        version
    )



    if java and java != "java":

        command[0] = java



    print(
        "Starting Minecraft..."
    )



    subprocess.run(

        command,

        cwd=MINECRAFT_DIR

    )
# ==============================
# PROGRAM START
# ==============================


if __name__ == "__main__":


    try:


        args = get_arguments()



        config = load_configuration()



        name = args.name.strip()



        version = args.version.strip()



        if not name:

            name = "Player"



        if not version:


            print(
                "No version selected"
            )


            exit()



        config["last_username"] = name

        config["last_version"] = version



        save_configuration(
            config
        )



        print(
            "=============================="
        )


        print(
            "Simple Launcher"
        )


        print(
            "MCF:",
            MINECRAFT_DIR
        )


        print(
            "Player:",
            name
        )


        print(
            "Version:",
            version
        )


        print(
            "=============================="
        )



        launch_minecraft(

            name,

            version

        )



    except Exception as error:


        print(
            "Launcher Error:"
        )


        print(
            error
        )