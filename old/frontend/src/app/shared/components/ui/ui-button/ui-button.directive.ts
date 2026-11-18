import { Directive, Input, HostBinding } from '@angular/core';

@Directive({
    selector: 'button[uiButton], a[uiButton]',
    standalone: true
})
export class UiButtonDirective {
    @Input() variant: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline' = 'primary';
    @Input() size: 'sm' | 'md' | 'lg' = 'md';
    @Input() fullWidth = false;

    @HostBinding('class.btn') baseClass = true;

    @HostBinding('class.btn-primary') get isPrimary() { return this.variant === 'primary'; }
    @HostBinding('class.btn-secondary') get isSecondary() { return this.variant === 'secondary'; }
    @HostBinding('class.btn-danger') get isDanger() { return this.variant === 'danger'; }
    @HostBinding('class.btn-ghost') get isGhost() { return this.variant === 'ghost'; }
    @HostBinding('class.btn-outline') get isOutline() { return this.variant === 'outline'; }

    @HostBinding('class.btn-sm') get isSmall() { return this.size === 'sm'; }
    @HostBinding('class.btn-lg') get isLarge() { return this.size === 'lg'; }

    @HostBinding('class.w-full') get isFullWidth() { return this.fullWidth; } // Assuming utility class exists or we style it
}
