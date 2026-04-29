package com.ozkanilkay.musiki_frontend

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.hilt.navigation.compose.hiltViewModel
import com.ozkanilkay.musiki_frontend.data.local.ThemePreferences
import com.ozkanilkay.musiki_frontend.player.PlayerViewModel
import com.ozkanilkay.musiki_frontend.ui.navigation.MusikiNavGraph
import com.ozkanilkay.musiki_frontend.ui.theme.MusikiTheme
import com.ozkanilkay.musiki_frontend.ui.theme.ThemeMode
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject lateinit var themePreferences: ThemePreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val themeMode by themePreferences.themeMode.collectAsState(initial = ThemeMode.DARK)

            MusikiTheme(themeMode = themeMode) {
                // Activity-scoped PlayerViewModel — survives navigation changes
                val playerViewModel: PlayerViewModel = hiltViewModel()
                MusikiNavGraph(playerViewModel = playerViewModel)
            }
        }
    }
}
