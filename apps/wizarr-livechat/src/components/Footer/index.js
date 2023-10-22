import { PopoverMenu } from '../Menu';
import { createClassName } from '../helpers';
import { h } from 'preact';
import styles from './styles.scss';
import { withTranslation } from 'react-i18next';

export const Footer = ({ children, className, ...props }) => (
	<footer className={createClassName(styles, 'footer', {}, [className])} {...props}>
		{children}
	</footer>
);


export const FooterContent = ({ children, className, ...props }) => (
	<div className={createClassName(styles, 'footer__content', {}, [className])} {...props}>
		{children}
	</div>
);

const handleMouseUp = ({ target }) => target.blur();

const OptionsTrigger = withTranslation()(({ pop, t }) => (
	<button className={createClassName(styles, 'footer__options')} onClick={pop} onMouseUp={handleMouseUp}>
		{t('options')}
	</button>
));


export const FooterOptions = ({ children }) => (
	<PopoverMenu trigger={OptionsTrigger} overlayed>
		{children}
	</PopoverMenu>
);


export const CharCounter = ({ className, style = {}, textLength, limitTextLength }) => (
	<span
		className={createClassName(styles, 'footer__remainder', { highlight: textLength === limitTextLength }, [className])}
		style={style}
	>
		{textLength} / {limitTextLength}
	</span>
);
