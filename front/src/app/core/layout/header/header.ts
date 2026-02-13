import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../auth/auth.service';
import { CommonModule } from '@angular/common';
import { JarvisAvatarComponent } from '../../../shared/components/jarvis-avatar/jarvis-avatar.component';
import { SystemHud } from '../../../shared/components/ui/system-hud/system-hud'; // Importar SystemHud

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, CommonModule, JarvisAvatarComponent, SystemHud],
  templateUrl: './header.html',
  styleUrl: './header.scss'
})
export class Header {
  private auth = inject(AuthService);

  isMenuOpen = false;
  isAuthenticated$ = this.auth.isAuthenticated$;

  // metrics$ logic removed in favor of SystemHud component

  toggleMenu() {
    this.isMenuOpen = !this.isMenuOpen;
  }

  closeMenu() {
    this.isMenuOpen = false;
  }

  logout() {
    this.auth.logout();
  }
}
