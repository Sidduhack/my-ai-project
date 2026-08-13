import { HTMLAttributes, forwardRef } from 'react';
import { cn } from '../../utils/helpers';
import { getStatusColor, getPriorityColor } from '../../utils/helpers';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'status' | 'priority';
  status?: string;
  priority?: string;
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'default', status, priority, ...props }, ref) => {
    const variants = {
      default: 'bg-primary text-primary-foreground hover:bg-primary/80',
      secondary: 'bg-dark-100 text-dark-900 dark:bg-dark-700 dark:text-dark-100',
      destructive: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
      outline: 'text-dark-700 dark:text-dark-300 border border-dark-300 dark:border-dark-600',
      status: status ? getStatusColor(status) : 'bg-gray-100 text-gray-700',
      priority: priority ? getPriorityColor(priority) : 'bg-gray-100 text-gray-700',
    };

    return (
      <span
        ref={ref}
        className={cn(
          'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors',
          variants[variant],
          className
        )}
        {...props}
      />
    );
  }
);
Badge.displayName = 'Badge';