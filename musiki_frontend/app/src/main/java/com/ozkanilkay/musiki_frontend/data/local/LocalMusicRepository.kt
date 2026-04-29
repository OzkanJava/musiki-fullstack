package com.ozkanilkay.musiki_frontend.data.local

import android.content.ContentUris
import android.content.Context
import android.net.Uri
import android.provider.MediaStore
import com.ozkanilkay.musiki_frontend.data.model.LocalTrack
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class LocalMusicRepository @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    suspend fun scanDeviceAudio(): List<LocalTrack> = withContext(Dispatchers.IO) {
        val collection = MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
        val projection = arrayOf(
            MediaStore.Audio.Media._ID,
            MediaStore.Audio.Media.TITLE,
            MediaStore.Audio.Media.ARTIST,
            MediaStore.Audio.Media.ALBUM,
            MediaStore.Audio.Media.ALBUM_ID,
            MediaStore.Audio.Media.DURATION,
            MediaStore.Audio.Media.RELATIVE_PATH,
        )
        val selection = "${MediaStore.Audio.Media.IS_MUSIC} != 0 AND " +
            "(${MediaStore.Audio.Media.RELATIVE_PATH} LIKE 'Music/%' " +
            "OR ${MediaStore.Audio.Media.RELATIVE_PATH} LIKE 'Download/%')"
        val sortOrder = "${MediaStore.Audio.Media.TITLE} COLLATE NOCASE ASC"
        val albumArtBase = Uri.parse("content://media/external/audio/albumart")

        val tracks = mutableListOf<LocalTrack>()
        context.contentResolver.query(collection, projection, selection, null, sortOrder)?.use { cursor ->
            val idCol = cursor.getColumnIndexOrThrow(MediaStore.Audio.Media._ID)
            val titleCol = cursor.getColumnIndexOrThrow(MediaStore.Audio.Media.TITLE)
            val artistCol = cursor.getColumnIndexOrThrow(MediaStore.Audio.Media.ARTIST)
            val albumCol = cursor.getColumnIndexOrThrow(MediaStore.Audio.Media.ALBUM)
            val albumIdCol = cursor.getColumnIndexOrThrow(MediaStore.Audio.Media.ALBUM_ID)
            val durationCol = cursor.getColumnIndexOrThrow(MediaStore.Audio.Media.DURATION)

            while (cursor.moveToNext()) {
                val id = cursor.getLong(idCol)
                val albumId = cursor.getLong(albumIdCol)
                tracks += LocalTrack(
                    id = id,
                    title = cursor.getString(titleCol) ?: "Bilinmeyen",
                    artist = cursor.getString(artistCol) ?: "Bilinmeyen Sanatçı",
                    album = cursor.getString(albumCol),
                    durationMs = cursor.getLong(durationCol),
                    contentUri = ContentUris.withAppendedId(collection, id),
                    albumArtUri = ContentUris.withAppendedId(albumArtBase, albumId),
                )
            }
        }
        tracks
    }
}
