package com.ozkanilkay.musiki_frontend.ui.navigation

sealed class Screen(val route: String) {
    // Auth
    object Login    : Screen("login")
    object Register : Screen("register")

    // Main
    object Home      : Screen("home")
    object Search    : Screen("search")
    object Recognize : Screen("recognize")
    object Upload    : Screen("upload")
    object Library   : Screen("library")
    object Profile   : Screen("profile")

    // Library sub-screens
    object LikedSongs       : Screen("library/liked-songs")
    object PlaylistList     : Screen("library/playlists")
    object CreatePlaylist   : Screen("library/playlists/create")
    object LocalMusic       : Screen("library/local-music")
    object PlaylistDetail   : Screen("library/playlists/{id}") {
        fun buildRoute(id: Int) = "library/playlists/$id"
    }

    // Detail
    object AlbumDetail : Screen("album/{id}") {
        fun buildRoute(id: Int) = "album/$id"
    }
    object ArtistDetail : Screen("artist/{id}") {
        fun buildRoute(id: Int) = "artist/$id"
    }

    // Player
    object Player : Screen("player")
}
