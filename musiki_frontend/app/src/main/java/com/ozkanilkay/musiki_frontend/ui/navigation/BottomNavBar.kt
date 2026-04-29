package com.ozkanilkay.musiki_frontend.ui.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.GraphicEq
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.LibraryMusic
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import androidx.navigation.compose.currentBackStackEntryAsState
import com.ozkanilkay.musiki_frontend.ui.theme.Musiki

private data class NavItem(
    val screen: Screen,
    val label: String,
    val icon: ImageVector,
)

private val navItems = listOf(
    NavItem(Screen.Home,      "Ana Sayfa",  Icons.Default.Home),
    NavItem(Screen.Search,    "Ara",        Icons.Default.Search),
    NavItem(Screen.Recognize, "Tanı",       Icons.Default.GraphicEq),
    NavItem(Screen.Library,   "Kütüphane",  Icons.Default.LibraryMusic),
    NavItem(Screen.Profile,   "Profil",     Icons.Default.Person),
)

@Composable
fun BottomNavBar(navController: NavController) {
    val backStack by navController.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route
    val c = Musiki.colors

    NavigationBar(containerColor = c.background, tonalElevation = 0.dp) {
        navItems.forEach { item ->
            NavigationBarItem(
                selected = currentRoute == item.screen.route,
                onClick = {
                    if (currentRoute != item.screen.route) {
                        navController.navigate(item.screen.route) {
                            popUpTo(Screen.Home.route) { saveState = true }
                            launchSingleTop = true
                            restoreState = true
                        }
                    }
                },
                icon = { Icon(item.icon, contentDescription = item.label) },
                label = { Text(item.label) },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor   = c.primary,
                    selectedTextColor   = c.primary,
                    unselectedIconColor = c.textSecondary,
                    unselectedTextColor = c.textSecondary,
                    indicatorColor      = c.outline,
                ),
            )
        }
    }
}
