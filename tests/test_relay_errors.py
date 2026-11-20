from pathlib import Path
import sys, requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from relay import friendly_error
error=requests.ReadTimeout('HTTPConnectionPool: Read timed out (read timeout=5)')
assert 'TV' in friendly_error(error,'tv') and 'YouTube' not in friendly_error(error,'tv')
assert 'relais vidéo local' in friendly_error(error,'relay')
assert 'YouTube' in friendly_error(error,'youtube')
assert '480p' not in friendly_error(error,'tv')
assert friendly_error(ValueError('La TV a refusé Play'),'tv')=='La TV a refusé Play'
assert 'https://' not in friendly_error(ValueError('Erreur https://media.example/secret-token'),'device')
print('Erreurs distinguées : TV, relais local et YouTube ; refus explicites conservés et URL masquées.')
