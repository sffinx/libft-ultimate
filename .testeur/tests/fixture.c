/* Internal verification fixture, not an implementation for student submission.
 * Delegates standard functions to libc, intentionally fails submission rules. */
#define _DEFAULT_SOURCE
#include "libft.h"
#include <string.h>
#include <strings.h>
#include <ctype.h>
#include <stdint.h>
#include <limits.h>
#include <unistd.h>
#include <stdio.h>
#ifndef MUTATION
# define MUTATION 0
#endif

int ft_isalpha(int c) { return MUTATION==1 ? isalpha(c) : !!isalpha(c); }
int ft_isdigit(int c) { return !!isdigit(c); }
int ft_isalnum(int c) { return !!isalnum(c); }
int ft_isascii(int c) { return c>=0 && c<=127; }
int ft_isprint(int c) { return !!isprint(c); }
int ft_toupper(int c) { return toupper(c); }
int ft_tolower(int c) { return tolower(c); }
size_t ft_strlen(const char *s) {
    if(MUTATION==21) exit(0);
    if(MUTATION==2) return strlen(s)+1;
    if(MUTATION==3) { volatile char x=s[strlen(s)+1]; (void)x; }
    if(MUTATION==4) for(;;) { __asm__ volatile(""); }
    return strlen(s);
}
void *ft_memset(void *p,int c,size_t n) { if(MUTATION==5) memset(p,c,n+1); return memset(p,c,n); }
void ft_bzero(void *p,size_t n) { bzero(p,n); }
void *ft_memcpy(void *d,const void *s,size_t n) { memcpy(d,s,n); return MUTATION==6 ? NULL : d; }
void *ft_memmove(void *d,const void *s,size_t n) {
    if(MUTATION==7) { for(size_t i=0;i<n;i++) ((char*)d)[i]=((char*)s)[i]; return d; }
    return memmove(d,s,n);
}
size_t ft_strlcpy(char *d,const char *s,size_t n) {
    size_t len=strlen(s);
    if(n) { size_t take=len<n-1?len:n-1; memcpy(d,s,take); d[take]=0; }
    return MUTATION==8 && n && len>=n ? n-1 : len;
}
size_t ft_strlcat(char *d,const char *s,size_t n) {
    size_t used=strnlen(d,n),len=strlen(s);
    if(used<n) ft_strlcpy(d+used,s,n-used);
    return used+len;
}
char *ft_strchr(const char *s,int c) { return MUTATION==9 && !c ? NULL : (char *)strchr(s,c); }
char *ft_strrchr(const char *s,int c) { return (char *)strrchr(s,c); }
int ft_strncmp(const char *a,const char *b,size_t n) {
    int x=strncmp(a,b,n);
    return MUTATION==10 ? -x : MUTATION==30 ? (x>0)-(x<0) : x;
}
void *ft_memchr(const void *s,int c,size_t n) { return (void *)memchr(s,c,n); }
int ft_memcmp(const void *a,const void *b,size_t n) {
    int x=memcmp(a,b,n);
    return MUTATION==30 ? ((x>0)-(x<0))*17 : x;
}
char *ft_strnstr(const char *s,const char *needle,size_t n) {
    size_t len=strlen(needle);
    if(!len) return (char *)s;
    for(size_t i=0;i<n && s[i];i++)
        if(len<=n-i && strncmp(s+i,needle,len)==0) return (char *)s+i;
    return NULL;
}
int ft_atoi(const char *s) { return atoi(s); }
void *ft_calloc(size_t n,size_t size) {
    if(MUTATION==11 && (!n || !size)) return NULL;
    if(size && n>SIZE_MAX/size) return NULL;
    size_t bytes=n*size;
    void *p=malloc(bytes?bytes:1);
    if(p && MUTATION!=12) memset(p,0,bytes);
    return p;
}
char *ft_strdup(const char *s) {
    size_t len=strlen(s)+1;
    char *p=malloc(len+(MUTATION==30?16:0));
    if(MUTATION==13 && !p) { volatile char *q=p; *q=0; }
    if(MUTATION==22 && p) { volatile char x=p[len]; (void)x; }
    if(p) memcpy(p,s,len);
    return p;
}
char *ft_substr(const char *s,unsigned int start,size_t n) {
    size_t len=strlen(s),take=0;
    if(start<len) { s+=start; take=len-start; if(take>n) take=n; }
    char *p=malloc(take+1);
    if(p) { memcpy(p,s,take); p[take]=0; }
    return p;
}
char *ft_strjoin(const char *a,const char *b) {
    size_t na=strlen(a),nb=strlen(b);
    char *p=malloc(na+nb+1);
    if(p) { memcpy(p,a,na); memcpy(p+na,b,nb+1); }
    return p;
}
char *ft_strtrim(const char *s,const char *set) {
    while(*s && strchr(set,*s)) s++;
    size_t n=strlen(s);
    while(n && strchr(set,s[n-1])) n--;
    return ft_substr(s,0,n);
}
char **ft_split(const char *s,char c) {
    size_t count=0;
    for(size_t i=0;s[i];) {
        if(s[i]==c) i++;
        else { count++; while(s[i] && s[i]!=c) i++; }
    }
    char **p=malloc((count+1)*sizeof(*p));
    if(!p) return NULL;
    size_t j=0;
    while(*s) {
        if(*s==c) { s++; continue; }
        size_t n=0; while(s[n] && s[n]!=c) n++;
        p[j]=ft_substr(s,0,n);
        if(!p[j]) {
            if(MUTATION!=14) { while(j) free(p[--j]); free(p); }
            return NULL;
        }
        j++; s+=n;
    }
    p[j]=NULL;
    return p;
}
char *ft_itoa(int n) { char b[32]; snprintf(b,sizeof(b),"%d",n); return ft_strdup(b); }
char *ft_strmapi(const char *s,char (*f)(unsigned int,char)) {
    size_t n=strlen(s); char *p=malloc(n+1);
    if(p) { for(size_t i=0;i<n;i++) p[i]=f(i,s[i]); p[n]=0; }
    return p;
}
void ft_striteri(char *s,void (*f)(unsigned int,char *)) {
    for(unsigned int i=0;s[i];i++) f(MUTATION==15?0:i,s+i);
}
void ft_putchar_fd(char c,int fd) { (void)write(fd,&c,1); }
void ft_putstr_fd(char *s,int fd) { (void)write(MUTATION==16?1:fd,s,strlen(s)); }
void ft_putendl_fd(char *s,int fd) { ft_putstr_fd(s,fd); ft_putchar_fd('\n',fd); }
void ft_putnbr_fd(int n,int fd) { char b[32]; int len=snprintf(b,sizeof(b),"%d",n); (void)write(fd,b,(size_t)len); }
t_list *ft_lstnew(void *p) { t_list *n=malloc(sizeof(*n)); if(n) { n->content=p; n->next=NULL; } return n; }
void ft_lstadd_front(t_list **lst,t_list *n) { n->next=*lst; *lst=n; }
unsigned int ft_lstsize(t_list *p) { unsigned int n=0; while(p) { n++; p=p->next; } return n; }
t_list *ft_lstlast(t_list *p) { while(p && p->next) p=p->next; return p; }
void ft_lstadd_back(t_list **lst,t_list *n) { if(*lst) ft_lstlast(*lst)->next=n; else *lst=n; }
void ft_lstdelone(t_list *p,void (*del)(void *)) { del(p->content); if(MUTATION!=17) free(p); }
void ft_lstclear(t_list **lst,void (*del)(void *)) {
    t_list *p=*lst;
    while(p) { t_list *next=p->next; ft_lstdelone(p,del); p=next; }
    if(MUTATION!=18) *lst=NULL;
}
void ft_lstiter(t_list *p,void (*f)(void *)) { while(p) { f(p->content); p=p->next; } }
t_list *ft_lstmap(t_list *lst,void *(*f)(void *),void (*del)(void *)) {
    t_list *head=NULL, **tail=&head;
    while(lst) {
        void *content=f(lst->content);
        if(MUTATION==19 && !content) { ft_lstclear(&head,del); return NULL; }
        t_list *node=ft_lstnew(content);
        if(!node) { if(MUTATION!=20) del(content); ft_lstclear(&head,del); return NULL; }
        *tail=node; tail=&node->next; lst=lst->next;
    }
    return head;
}
