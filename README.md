# fritzprofiles

A tool to switch the online time of profiles in the AVM Fritz!Box.

Can be used as a python package or with the supplied commandlinetool `fritzprofiles`.

Example usage (from command line):

```bash
fritzprofiles --user <user> --password <password> --url 192.168.178.1 --get_state --profile Gesperrt --set_state unlimited
```

You can retrieve a list of all profiles by using (`--get_all`):

```bash
fritzprofiles --user <user> --password <password> --url 192.168.178.1 --get_all
```

Modified from https://github.com/flopp/fritz-switch-profiles
