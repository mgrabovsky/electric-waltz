library(patchwork)
library(tidyverse)

theme_set(theme_classic())

d <- cbind(
  read_csv('input_data.csv',
           col_names = c('demand', 'pv_util', 'wind_util')),
  read_csv('model_output.csv')
) %>% as_tibble() %>%
  mutate(ix = 1:nrow(.) - 1,
         dt = as.POSIXct(3600 * ix, tz = 'UTC+1', origin = '2050-01-01 00:00'),
         .before = 'demand') %>%
  mutate(storage = pumped + battery + p2g)

plot_power_series <- function(df) {
  select(df, dt, nuclear:gas, import, storage, shortage) %>%
    pivot_longer(-dt, names_to = 'type', values_to = 'power') %>%
    mutate(type = fct_rev(fct_relevel(type, 'nuclear', 'gas', 'biomass', 'pv', 'wind',
                                      'hydro', 'import', 'storage', 'shortage'))) %>%
    ggplot(aes(dt, power)) +
    geom_area(aes(fill = type)) +
    geom_line(aes(y = demand * 1.0703),
              data = select(df, dt, demand),
              size = 1) +
    xlab('Day of year') +
    scale_y_continuous('Instant power (GW)',
                       labels = scales::label_comma(1, scale = 1e-3)) +
    scale_fill_manual('Source type',
                      values = c(
                        nuclear = 'firebrick',
                        pv      = 'gold',
                        wind    = '#223966',
                        biomass = '#8ea277',
                        hydro   = '#3e5f9f',
                        gas     = 'black',
                        import  = '#c6c6c6',
                        storage = '#efefef',
                        shortage = 'pink'
                      ),
                      labels = c('Nuclear', 'Photovoltaic', 'On-shore wind',
                                 'Biomass', 'Hydro', 'Nat. gas',
                                 'Import/export', 'Storage dis/charging', 'Shortage/dump')) +
    coord_cartesian(expand = FALSE) +
    theme(legend.position = 'bottom')
}

# Plot first week of the year.
p1 <- plot_power_series(slice(d, 1:(2*168))) +
  theme(axis.title.x    = element_blank(),
        legend.position = 'none')
# Plot a week roughly in the mid-year.
p2 <- plot_power_series(slice(d, (25*168):(27*168)))

p1 / p2