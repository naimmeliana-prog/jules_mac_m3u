# jules_mac_m3u

Herramienta para convertir un portal MAC Stalker a una URL M3U auto-actualizable con categorías.

Esta herramienta está diseñada para ejecutarse automáticamente mediante GitHub Actions y generar varios archivos `.m3u` en este repositorio, divididos por tipo y lenguaje, los cuales puedes usar directamente en cualquier reproductor IPTV proporcionando la URL en crudo (Raw).

## Características

- Filtrado de Live TV por idiomas: Español (ES), Francés (FR) e Inglés (UK/EN).
- Filtrado de VOD por idiomas: Español (ES) y Francés (FR).
- Filtrado de Series por idiomas: Español (ES) y Francés (FR).
- Carga de metadatos completos para Películas y Series (Sinopsis, Año, Director, Reparto, Póster/Logo).
- Generación y extracción correcta de temporadas y episodios de Series utilizando el formato de token Base64 de portales MAC Stalker.
- Auto-actualizable y gratuita: Utiliza GitHub Actions para ejecutarse cada noche (escalonado) y subir los cambios a este repositorio.

## Enlaces M3U auto-actualizables

Copia los enlaces a la versión "Raw" de los archivos una vez que GitHub Actions genere la lista:

### TV
- **TV Español:** `https://raw.githubusercontent.com/naimmeliana-prog/jules_mac_m3u/main/tv_es.m3u`
- **TV Francés:** `https://raw.githubusercontent.com/naimmeliana-prog/jules_mac_m3u/main/tv_fr.m3u`
- **TV Inglés:** `https://raw.githubusercontent.com/naimmeliana-prog/jules_mac_m3u/main/tv_en.m3u`

### VOD (Películas)
- **VOD Español:** `https://raw.githubusercontent.com/naimmeliana-prog/jules_mac_m3u/main/vod_es.m3u`
- **VOD Francés:** `https://raw.githubusercontent.com/naimmeliana-prog/jules_mac_m3u/main/vod_fr.m3u`

### Series
- **Series Español:** `https://raw.githubusercontent.com/naimmeliana-prog/jules_mac_m3u/main/series_es.m3u`
- **Series Francés:** `https://raw.githubusercontent.com/naimmeliana-prog/jules_mac_m3u/main/series_fr.m3u`
