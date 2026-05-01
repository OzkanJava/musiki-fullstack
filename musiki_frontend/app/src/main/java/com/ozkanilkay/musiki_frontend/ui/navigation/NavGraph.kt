package com.ozkanilkay.musiki_frontend.ui.navigation

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.ozkanilkay.musiki_frontend.player.PlayerViewModel
import com.ozkanilkay.musiki_frontend.ui.auth.LoginScreen
import com.ozkanilkay.musiki_frontend.ui.auth.RegisterScreen
import com.ozkanilkay.musiki_frontend.ui.auth.SessionState
import com.ozkanilkay.musiki_frontend.ui.auth.SessionViewModel
import com.ozkanilkay.musiki_frontend.ui.detail.AlbumDetailScreen
import com.ozkanilkay.musiki_frontend.ui.detail.ArtistDetailScreen
import com.ozkanilkay.musiki_frontend.ui.home.HomeScreen
import com.ozkanilkay.musiki_frontend.ui.library.LibraryScreen
import com.ozkanilkay.musiki_frontend.ui.library.LikedSongsScreen
import com.ozkanilkay.musiki_frontend.ui.library.LocalMusicScreen
import com.ozkanilkay.musiki_frontend.ui.player.FullPlayerScreen
import com.ozkanilkay.musiki_frontend.ui.player.MiniPlayerBar
import com.ozkanilkay.musiki_frontend.ui.playlist.CreatePlaylistScreen
import com.ozkanilkay.musiki_frontend.ui.playlist.PlaylistDetailScreen
import com.ozkanilkay.musiki_frontend.ui.playlist.PlaylistListScreen
import com.ozkanilkay.musiki_frontend.ui.profile.ProfileScreen
import com.ozkanilkay.musiki_frontend.ui.recognize.RecognizeScreen
import com.ozkanilkay.musiki_frontend.ui.search.SearchScreen
import com.ozkanilkay.musiki_frontend.ui.upload.UploadScreen

private val mainRoutes = setOf(
    Screen.Home.route,
    Screen.Search.route,
    Screen.Recognize.route,
    Screen.Library.route,
    Screen.Profile.route,
)

// Mini-player main ekranlar + library/upload alt ekranlarda da görünsün
private val miniPlayerRoutes = mainRoutes + setOf(
    Screen.LikedSongs.route,
    Screen.PlaylistList.route,
    Screen.PlaylistDetail.route,
    Screen.LocalMusic.route,
    Screen.AlbumDetail.route,
    Screen.ArtistDetail.route,
    Screen.Upload.route,
)

@Composable
fun MusikiNavGraph(
    playerViewModel: PlayerViewModel,
    sessionViewModel: SessionViewModel = hiltViewModel(),
) {
    val navController: NavHostController = rememberNavController()

    val sessionState by sessionViewModel.sessionState.collectAsState()

    if (sessionState == SessionState.Loading) return

    val startDestination = when (sessionState) {
        SessionState.Authenticated -> Screen.Home.route
        else -> Screen.Login.route
    }

    LaunchedEffect(sessionState) {
        if (sessionState == SessionState.Unauthenticated) {
            navController.navigate(Screen.Login.route) {
                popUpTo(0) { inclusive = true }
            }
        }
    }

    val backStack by navController.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route
    val isAuthRoute = currentRoute == Screen.Login.route || currentRoute == Screen.Register.route
    val isFullPlayer = currentRoute == Screen.Player.route
    val showBottomBar = !isAuthRoute && !isFullPlayer && currentRoute != null

    val currentSong by playerViewModel.currentSong.collectAsState()
    val showMiniPlayer = currentSong != null && currentRoute in miniPlayerRoutes

    Scaffold(
        bottomBar = {
            Column {
                if (showMiniPlayer) {
                    MiniPlayerBar(
                        playerViewModel = playerViewModel,
                        onExpand = { navController.navigate(Screen.Player.route) },
                    )
                }
                if (showBottomBar) {
                    BottomNavBar(navController = navController)
                }
            }
        },
    ) { innerPadding ->
        NavHost(
            navController    = navController,
            startDestination = startDestination,
            modifier         = Modifier.padding(innerPadding),
        ) {
            // ── Auth ──────────────────────────────────────────────────────────
            composable(Screen.Login.route) {
                LoginScreen(
                    onLoginSuccess = {
                        navController.navigate(Screen.Home.route) {
                            popUpTo(Screen.Login.route) { inclusive = true }
                        }
                    },
                    onNavigateToRegister = { navController.navigate(Screen.Register.route) },
                )
            }
            composable(Screen.Register.route) {
                RegisterScreen(
                    onRegisterSuccess = {
                        navController.navigate(Screen.Home.route) {
                            popUpTo(0) { inclusive = true }
                        }
                    },
                    onNavigateBack = { navController.popBackStack() },
                )
            }

            // ── Main ──────────────────────────────────────────────────────────
            composable(Screen.Home.route) {
                HomeScreen(
                    playerViewModel = playerViewModel,
                    onOpenArtist = { id -> navController.navigate(Screen.ArtistDetail.buildRoute(id)) },
                )
            }
            composable(Screen.Search.route) {
                SearchScreen(
                    playerViewModel = playerViewModel,
                    onOpenArtist = { id -> navController.navigate(Screen.ArtistDetail.buildRoute(id)) },
                )
            }
            composable(Screen.Recognize.route) {
                RecognizeScreen(
                    onOpenArtist = { id -> navController.navigate(Screen.ArtistDetail.buildRoute(id)) },
                    onOpenAlbum  = { id -> navController.navigate(Screen.AlbumDetail.buildRoute(id)) },
                )
            }
            composable(Screen.Upload.route) {
                UploadScreen(onBack = { navController.popBackStack() })
            }
            composable(Screen.Profile.route) {
                ProfileScreen(
                    onLogout = {
                        navController.navigate(Screen.Login.route) {
                            popUpTo(0) { inclusive = true }
                        }
                    },
                    onNavigateToUpload = { navController.navigate(Screen.Upload.route) },
                )
            }

            // ── Library ───────────────────────────────────────────────────────
            composable(Screen.Library.route) {
                LibraryScreen(
                    onNavigate = { route -> navController.navigate(route) },
                )
            }
            composable(Screen.LikedSongs.route) {
                LikedSongsScreen(
                    playerViewModel = playerViewModel,
                    onBack = { navController.popBackStack() },
                    onOpenArtist = { id -> navController.navigate(Screen.ArtistDetail.buildRoute(id)) },
                )
            }
            composable(Screen.LocalMusic.route) {
                LocalMusicScreen(
                    playerViewModel = playerViewModel,
                    onBack = { navController.popBackStack() },
                )
            }
            composable(Screen.PlaylistList.route) {
                PlaylistListScreen(
                    onBack = { navController.popBackStack() },
                    onOpenPlaylist = { id ->
                        navController.navigate(Screen.PlaylistDetail.buildRoute(id))
                    },
                    onCreate = { navController.navigate(Screen.CreatePlaylist.route) },
                )
            }
            composable(Screen.CreatePlaylist.route) {
                CreatePlaylistScreen(
                    onBack = { navController.popBackStack() },
                    onCreated = { navController.popBackStack() },
                )
            }
            composable(
                route = Screen.PlaylistDetail.route,
                arguments = listOf(navArgument("id") { type = NavType.IntType }),
            ) { entry ->
                val id = entry.arguments?.getInt("id") ?: return@composable
                PlaylistDetailScreen(
                    playlistId = id,
                    playerViewModel = playerViewModel,
                    onBack = { navController.popBackStack() },
                )
            }

            // ── Album / Artist Detail ─────────────────────────────────────────
            composable(
                route = Screen.AlbumDetail.route,
                arguments = listOf(navArgument("id") { type = NavType.IntType }),
            ) { entry ->
                val id = entry.arguments?.getInt("id") ?: return@composable
                AlbumDetailScreen(
                    onBack = { navController.popBackStack() },
                    onArtistClick = { artistId ->
                        navController.navigate(Screen.ArtistDetail.buildRoute(artistId))
                    },
                    playerViewModel = playerViewModel,
                )
            }
            composable(
                route = Screen.ArtistDetail.route,
                arguments = listOf(navArgument("id") { type = NavType.IntType }),
            ) { entry ->
                val id = entry.arguments?.getInt("id") ?: return@composable
                ArtistDetailScreen(
                    onBack = { navController.popBackStack() },
                    onAlbumClick = { albumId ->
                        navController.navigate(Screen.AlbumDetail.buildRoute(albumId))
                    },
                    playerViewModel = playerViewModel,
                )
            }

            // ── Full Player ───────────────────────────────────────────────────
            composable(Screen.Player.route) {
                FullPlayerScreen(
                    playerViewModel = playerViewModel,
                    onNavigateBack  = { navController.popBackStack() },
                    onOpenArtist    = { id ->
                        navController.navigate(Screen.ArtistDetail.buildRoute(id)) {
                            popUpTo(Screen.Player.route) { inclusive = true }
                        }
                    },
                )
            }
        }
    }
}
