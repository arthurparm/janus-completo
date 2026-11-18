import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../auth/auth.service';
import { CommonModule } from '@angular/common';
import { JarvisAvatarComponent } from '../../../shared/components/jarvis-avatar/jarvis-avatar.component';
import { SystemHud } from '../../../shared/components/ui/system-hud/system-hud'; // Importar SystemHud
import { Router } from '@angular/router';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, CommonModule, JarvisAvatarComponent, SystemHud],
  templateUrl: './header.html',
  styleUrl: './header.scss'
})
export class Header {
  private auth = inject(AuthService);
  private router = inject(Router);

  isMenuOpen = false;
  isAuthenticated$ = this.auth.isAuthenticated$;

  // metrics$ logic removed in favor of SystemHud component

  toggleMenu() {
    this.isMenuOpen = !this.isMenuOpen;
  }

  closeMenu() {
    this.isMenuOpen = false;
  }

  async logout(): Promise<void> {
    await this.auth.logout();
    this.closeMenu();
    await this.router.navigate(['/login']);
  }
}
