2026-06-24T20:59:33.638230841Z                    ^^^^^^^^^^^^^^^^^
2026-06-24T20:59:33.638234571Z   File "/opt/render/project/src/.venv/lib/python3.11/site-packages/django/utils/functional.py", line 57, in __get__
2026-06-24T20:59:33.638334613Z     res = instance.__dict__[self.name] = self.func(instance)
2026-06-24T20:59:33.638366514Z                                          ^^^^^^^^^^^^^^^^^^^
2026-06-24T20:59:33.638374294Z   File "/opt/render/project/src/.venv/lib/python3.11/site-packages/django/urls/resolvers.py", line 715, in url_patterns
2026-06-24T20:59:33.638546708Z     patterns = getattr(self.urlconf_module, "urlpatterns", self.urlconf_module)
2026-06-24T20:59:33.638552558Z                        ^^^^^^^^^^^^^^^^^^^
2026-06-24T20:59:33.638556358Z   File "/opt/render/project/src/.venv/lib/python3.11/site-packages/django/utils/functional.py", line 57, in __get__
2026-06-24T20:59:33.63865295Z     res = instance.__dict__[self.name] = self.func(instance)
2026-06-24T20:59:33.63865772Z                                          ^^^^^^^^^^^^^^^^^^^
2026-06-24T20:59:33.63865993Z   File "/opt/render/project/src/.venv/lib/python3.11/site-packages/django/urls/resolvers.py", line 708, in urlconf_module
2026-06-24T20:59:33.638870715Z     return import_module(self.urlconf_name)
2026-06-24T20:59:33.638880745Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-06-24T20:59:33.638883965Z   File "/opt/render/project/python/Python-3.11.8/lib/python3.11/importlib/__init__.py", line 126, in import_module
2026-06-24T20:59:33.638979377Z     return _bootstrap._gcd_import(name[level:], package, level)
2026-06-24T20:59:33.639035719Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-06-24T20:59:33.639040599Z   File "<frozen importlib._bootstrap>", line 1204, in _gcd_import
2026-06-24T20:59:33.639043639Z   File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
2026-06-24T20:59:33.639046529Z   File "<frozen importlib._bootstrap>", line 1147, in _find_and_load_unlocked
2026-06-24T20:59:33.639054239Z   File "<frozen importlib._bootstrap>", line 690, in _load_unlocked
2026-06-24T20:59:33.639057309Z   File "<frozen importlib._bootstrap_external>", line 940, in exec_module
2026-06-24T20:59:33.639060669Z   File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
2026-06-24T20:59:33.639064259Z   File "/opt/render/project/src/core/urls.py", line 18, in <module>
2026-06-24T20:59:33.639162581Z     path('', include('marketplace.urls')),
2026-06-24T20:59:33.639171492Z              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-06-24T20:59:33.639185982Z   File "/opt/render/project/src/.venv/lib/python3.11/site-packages/django/urls/conf.py", line 38, in include
2026-06-24T20:59:33.639325095Z     urlconf_module = import_module(urlconf_module)
2026-06-24T20:59:33.639335555Z                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-06-24T20:59:33.639338245Z   File "/opt/render/project/python/Python-3.11.8/lib/python3.11/importlib/__init__.py", line 126, in import_module
2026-06-24T20:59:33.639427087Z     return _bootstrap._gcd_import(name[level:], package, level)
2026-06-24T20:59:33.639463878Z            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-06-24T20:59:33.639466638Z   File "<frozen importlib._bootstrap>", line 1204, in _gcd_import
2026-06-24T20:59:33.639468748Z   File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
2026-06-24T20:59:33.639470698Z   File "<frozen importlib._bootstrap>", line 1147, in _find_and_load_unlocked
2026-06-24T20:59:33.639473178Z   File "<frozen importlib._bootstrap>", line 690, in _load_unlocked
2026-06-24T20:59:33.639477778Z   File "<frozen importlib._bootstrap_external>", line 940, in exec_module
2026-06-24T20:59:33.639479848Z   File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
2026-06-24T20:59:33.639482008Z   File "/opt/render/project/src/marketplace/urls.py", line 9, in <module>
2026-06-24T20:59:33.639579561Z     from . import views
2026-06-24T20:59:33.639583181Z   File "/opt/render/project/src/marketplace/views.py", line 31, in <module>
2026-06-24T20:59:33.639717304Z     from .growth_agent import execute_master_cycle
2026-06-24T20:59:33.639726434Z   File "/opt/render/project/src/marketplace/growth_agent.py", line 28, in <module>
2026-06-24T20:59:33.639834386Z     from .ai_utils import ask_ai_with_failover, clean_and_parse_json, ask_master_ai_smart
2026-06-24T20:59:33.639840696Z   File "/opt/render/project/src/marketplace/ai_utils.py", line 3, in <module>
2026-06-24T20:59:33.639942309Z     from .growth_agent import ask_ai_with_failover # ይህ በ Step 1 የተዘጋጀው ነው
2026-06-24T20:59:33.639949519Z     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2026-06-24T20:59:33.639952359Z ImportError: cannot import name 'ask_ai_with_failover' from partially initialized module 'marketplace.growth_agent' (most likely due to a circular import) (/opt/render/project/src/marketplace/growth_agent.py)
2026-06-24T20:59:35.576280017Z ==> Exited with status 1
2026-06-24T20:59:35.579305121Z ==> Common ways to troubleshoot your deploy: https://render.com/docs/troubleshooting-deploys
2026-06-24T20:59:41.747455409Z ==> Running 'python manage.py migrate --no-input && python create_admin.py && uvicorn core.asgi:application --host 0.0.0.0 --port 10000 --workers 1'