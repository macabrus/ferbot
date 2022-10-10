# FER Intranet automation tool

Prerequisites:
- install python poetry package manager
- [download webdriver binaries](https://chromedriver.chromium.org/downloads) for your version of browser
- configure environment variables with your FER Intranet credentials in example `.example.env` file

Then you can run script with:
```bash
poetry install
poetry run materijali
```

Verified to work on Chromium/Mac but should work just fine on any platform combo. If you find any issues,
feel free to open a Github issue. PRs are also welcome.